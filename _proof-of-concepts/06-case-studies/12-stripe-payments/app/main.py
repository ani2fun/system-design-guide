"""Composition root + HTTP adapter (FastAPI) for the payment system.

`charge` is the whole flow in one transaction: idempotency check → state machine
→ ledger postings → remember the result. Retries with the same key replay it.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import PG_DSN
from domain.errors import IllegalTransition
from domain.idempotency_guard import IdempotencyGuard
from domain.ledger_writer import LedgerWriter
from domain.model import Event, Posting, State
from domain.payment_intent_machine import PaymentIntentMachine
from domain.ports import PaymentUnitOfWork
from infra.db import create_pool
from infra.postgres import PostgresPaymentUnitOfWork


@dataclass(slots=True)
class Services:
    pool: asyncpg.Pool
    uow: PaymentUnitOfWork


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    pool = await create_pool(PG_DSN)
    _services = Services(pool, PostgresPaymentUnitOfWork(pool))
    try:
        yield
    finally:
        await pool.close()
        _services = None


async def charge(uow: PaymentUnitOfWork, key: str, amount: int, merchant: str) -> dict[str, object]:
    async with uow.transaction() as tx:
        guard = IdempotencyGuard(tx)
        stored = await guard.replay(key)
        if stored is not None:
            replayed: dict[str, object] = json.loads(stored)
            return replayed

        state = State.CREATED
        for event in (Event.AUTHORIZE, Event.CAPTURE):
            state = PaymentIntentMachine.next_state(state, event)

        payment_id = await tx.new_payment(merchant, amount, state.value)
        await LedgerWriter(tx).record([Posting("customer", -amount), Posting(f"merchant:{merchant}", amount)])

        result: dict[str, object] = {"payment_id": payment_id, "state": state.value, "amount": amount}
        await guard.remember(key, json.dumps(result))
        return result


app = FastAPI(title="Payment System POC", lifespan=lifespan)


class ChargeReq(BaseModel):
    idempotency_key: str
    amount: int
    merchant: str


class TransitionReq(BaseModel):
    state: State
    event: Event


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/charge")
async def charge_endpoint(req: ChargeReq) -> dict[str, object]:
    return await charge(services().uow, req.idempotency_key, req.amount, req.merchant)


@app.post("/transition")
async def transition(req: TransitionReq) -> dict[str, str]:
    try:
        return {"to_state": PaymentIntentMachine.next_state(req.state, req.event).value}
    except IllegalTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/balance/{account}")
async def balance(account: str) -> dict[str, object]:
    async with services().uow.transaction() as tx:
        return {"account": account, "balance": await tx.balance(account)}


@app.get("/stats")
async def stats() -> dict[str, int]:
    async with services().pool.acquire() as con:
        total = await con.fetchval("SELECT coalesce(sum(amount), 0) FROM ledger")
        payments = await con.fetchval("SELECT count(*) FROM payments")
    return {"ledger_sum": total, "payments": payments}

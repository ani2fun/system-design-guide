"""Composition root + HTTP adapter (FastAPI) for the Ticketmaster POC.

Builds the concrete adapters, injects them into the domain services, and
translates domain errors to HTTP. The domain owns the no-double-booking
invariant; this layer knows about FastAPI, Postgres, and Redis so the domain
doesn't have to.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis, from_url

from app.config import EVENT_ID, HOLD_TTL_MS, PG_DSN, RACE_DELAY, REDIS_URL, SEAT_COUNT
from domain.booking_confirmer import BookingConfirmer
from domain.errors import SeatUnavailableError
from domain.payment_client import PaymentClient
from domain.seat_hold_service import SeatHoldService
from infra.db import create_pool, seed_seats
from infra.payment import StubPaymentGateway
from infra.postgres import PostgresBookingUnitOfWork
from infra.redis_ import RedisSeatHoldStore


@dataclass(slots=True)
class Services:
    pool: asyncpg.Pool
    redis: Redis
    holds: SeatHoldService
    payment: PaymentClient
    confirmer: BookingConfirmer


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    pool = await create_pool(PG_DSN)
    await seed_seats(pool, EVENT_ID, SEAT_COUNT)
    redis: Redis = from_url(REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]

    holds = SeatHoldService(RedisSeatHoldStore(redis), ttl_ms=HOLD_TTL_MS)
    payment = PaymentClient(StubPaymentGateway())
    _services = Services(
        pool=pool,
        redis=redis,
        holds=holds,
        payment=payment,
        confirmer=BookingConfirmer(
            PostgresBookingUnitOfWork(pool), holds, payment, race_delay=RACE_DELAY
        ),
    )
    try:
        yield
    finally:
        await redis.aclose()
        await pool.close()
        _services = None


app = FastAPI(title="Ticketmaster POC", lifespan=lifespan)


class HoldReq(BaseModel):
    seat_id: str
    holder: str


class ConfirmReq(BaseModel):
    seat_id: str
    holder: str
    payment_key: str
    unsafe: bool = False


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/holds", status_code=201)
async def acquire_hold(req: HoldReq) -> dict[str, object]:
    ok = await services().holds.acquire(req.seat_id, req.holder)
    if not ok:
        held_by = await services().holds.holder(req.seat_id)
        raise HTTPException(status_code=409, detail=f"seat held by {held_by}")
    return {"seat_id": req.seat_id, "holder": req.holder, "held": True}


@app.post("/confirm", status_code=201)
async def confirm(req: ConfirmReq) -> dict[str, object]:
    try:
        order_id = await services().confirmer.confirm(
            req.seat_id, req.holder, req.payment_key, use_lock=not req.unsafe
        )
    except SeatUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"order_id": order_id, "seat_id": req.seat_id, "holder": req.holder}


@app.post("/reset")
async def reset() -> dict[str, bool]:
    svc = services()
    async with svc.pool.acquire() as con:
        await con.execute("DELETE FROM orders")
        await con.execute("UPDATE seats SET status = 'available', sold_to = NULL")
    keys = [k async for k in svc.redis.scan_iter("hold:*")]
    if keys:
        await svc.redis.delete(*keys)
    return {"reset": True}


@app.get("/seats/{seat_id}")
async def seat(seat_id: str) -> dict[str, object]:
    svc = services()
    async with svc.pool.acquire() as con:
        row = await con.fetchrow("SELECT status, sold_to FROM seats WHERE seat_id = $1", seat_id)
        orders = await con.fetchval("SELECT count(*) FROM orders WHERE seat_id = $1", seat_id)
    if row is None:
        raise HTTPException(status_code=404, detail="no such seat")
    return {"seat_id": seat_id, "status": row["status"], "sold_to": row["sold_to"], "orders": orders}


@app.get("/stats")
async def stats() -> dict[str, object]:
    svc = services()
    async with svc.pool.acquire() as con:
        sold = await con.fetchval("SELECT count(*) FROM seats WHERE status = 'sold'")
        order_count = await con.fetchval("SELECT count(*) FROM orders")
        oversold = await con.fetchval(
            "SELECT count(*) FROM (SELECT seat_id FROM orders GROUP BY seat_id HAVING count(*) > 1) t"
        )
    return {
        "seats_sold": sold,
        "orders": order_count,
        "double_sold_seats": oversold,
        "holds": svc.holds.status(),
        "confirms": svc.confirmer.status(),
        "payments": svc.payment.status(),
    }

"""Postgres adapter — the PaymentUnitOfWork port (infrastructure).

`reserve` is the linchpin: INSERT the idempotency key; if it already exists, a
concurrent charge blocks on the unique constraint until the first commits, then
reads the stored result — exactly-once by construction.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import asyncpg

from domain.model import Posting
from domain.ports import PaymentTransaction, PaymentUnitOfWork


class PostgresPaymentTransaction(PaymentTransaction):
    def __init__(self, con: asyncpg.Connection) -> None:
        self._con = con

    async def reserve(self, key: str) -> str | None:
        inserted = await self._con.fetchval(
            "INSERT INTO idempotency (key) VALUES ($1) ON CONFLICT DO NOTHING RETURNING key", key
        )
        if inserted is not None:
            return None  # first time — caller does the work
        result: str | None = await self._con.fetchval(
            "SELECT result::text FROM idempotency WHERE key = $1", key
        )
        return result

    async def save_result(self, key: str, result_json: str) -> None:
        await self._con.execute(
            "UPDATE idempotency SET result = $2::jsonb WHERE key = $1", key, result_json
        )

    async def new_payment(self, merchant: str, amount: int, state: str) -> int:
        payment_id: int = await self._con.fetchval(
            "INSERT INTO payments (merchant, amount, state) VALUES ($1, $2, $3) RETURNING id",
            merchant, amount, state,
        )
        return payment_id

    async def post(self, entries: list[Posting]) -> None:
        await self._con.executemany(
            "INSERT INTO ledger (account, amount) VALUES ($1, $2)",
            [(e.account, e.amount) for e in entries],
        )

    async def balance(self, account: str) -> int:
        total: int = await self._con.fetchval(
            "SELECT coalesce(sum(amount), 0) FROM ledger WHERE account = $1", account
        )
        return total


class PostgresPaymentUnitOfWork(PaymentUnitOfWork):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @asynccontextmanager
    async def _tx(self) -> AsyncIterator[PaymentTransaction]:
        async with self._pool.acquire() as con, con.transaction():
            yield PostgresPaymentTransaction(con)

    def transaction(self) -> AbstractAsyncContextManager[PaymentTransaction]:
        return self._tx()

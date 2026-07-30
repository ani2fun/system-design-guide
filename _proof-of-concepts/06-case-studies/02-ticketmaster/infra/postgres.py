"""Postgres adapter — the BookingUnitOfWork port (infrastructure).

Owns the transactional boundary the invariant needs: a connection-bound
transaction whose `lock_seat` issues `SELECT … FOR UPDATE`. asyncpg is imported
only here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import asyncpg

from domain.ports import BookingTransaction, BookingUnitOfWork


class PostgresBookingTransaction(BookingTransaction):
    def __init__(self, con: asyncpg.Connection) -> None:
        self._con = con

    async def lock_seat(self, seat_id: str, use_lock: bool) -> str | None:
        clause = "FOR UPDATE" if use_lock else ""
        status: str | None = await self._con.fetchval(
            f"SELECT status FROM seats WHERE seat_id = $1 {clause}", seat_id
        )
        return status

    async def mark_sold(self, seat_id: str, holder: str) -> None:
        await self._con.execute(
            "UPDATE seats SET status = 'sold', sold_to = $2 WHERE seat_id = $1", seat_id, holder
        )

    async def record_order(self, seat_id: str, holder: str) -> int:
        order_id: int = await self._con.fetchval(
            "INSERT INTO orders (seat_id, holder) VALUES ($1, $2) RETURNING id", seat_id, holder
        )
        return order_id


class PostgresBookingUnitOfWork(BookingUnitOfWork):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @asynccontextmanager
    async def _tx(self) -> AsyncIterator[BookingTransaction]:
        async with self._pool.acquire() as con:
            async with con.transaction():
                yield PostgresBookingTransaction(con)

    def transaction(self) -> AbstractAsyncContextManager[BookingTransaction]:
        return self._tx()

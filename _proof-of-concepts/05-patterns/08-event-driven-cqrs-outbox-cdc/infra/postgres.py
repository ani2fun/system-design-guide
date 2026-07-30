"""Postgres adapters (asyncpg): a real Unit of Work so the order row and its
outbox event commit in one transaction, plus the outbox store the relay polls.
"""

from __future__ import annotations

import asyncpg

from domain.model import Order, OutboxEvent, OutboxRecord
from domain.ports import Orders, Outbox, UnitOfWork


class PostgresOrders(Orders):
    def __init__(self, con: asyncpg.Connection) -> None:
        self._con = con

    async def add(self, order: Order) -> None:
        await self._con.execute(
            "INSERT INTO orders (id, customer, amount_cents) VALUES ($1, $2, $3)",
            order.id, order.customer, order.amount_cents,
        )


class PostgresOutbox(Outbox):
    def __init__(self, con: asyncpg.Connection) -> None:
        self._con = con

    async def add(self, event: OutboxEvent) -> None:
        await self._con.execute(
            "INSERT INTO outbox (event_id, aggregate_id, type, payload) "
            "VALUES ($1, $2, $3, $4)",
            event.event_id, event.aggregate_id, event.type, event.payload,
        )

    async def fetch_unsent(self, limit: int) -> list[OutboxRecord]:
        rows = await self._con.fetch(
            "SELECT seq, event_id, aggregate_id, type, payload FROM outbox "
            "WHERE NOT sent ORDER BY seq LIMIT $1 FOR UPDATE SKIP LOCKED",
            limit,
        )
        return [
            OutboxRecord(
                seq=r["seq"],
                event=OutboxEvent(r["event_id"], r["aggregate_id"], r["type"], r["payload"]),
            )
            for r in rows
        ]

    async def mark_sent(self, seqs: list[int]) -> None:
        if seqs:
            await self._con.execute("UPDATE outbox SET sent = true WHERE seq = ANY($1)", seqs)


class PostgresUnitOfWork(UnitOfWork):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        # asyncpg types resolve to Any (ignore_missing_imports), so None is fine
        # here and attribute access below is unrestricted.
        self._con: asyncpg.Connection = None
        self._tx: asyncpg.Transaction = None
        self._committed = False

    async def __aenter__(self) -> UnitOfWork:
        self._con = await self._pool.acquire()
        self._tx = self._con.transaction()
        await self._tx.start()
        self.orders = PostgresOrders(self._con)
        self.outbox = PostgresOutbox(self._con)
        self._committed = False
        return self

    async def commit(self) -> None:
        await self._tx.commit()
        self._committed = True

    async def rollback(self) -> None:
        await self._tx.rollback()

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        try:
            if not self._committed:
                await self._tx.rollback()  # error, or forgot to commit → undo
        finally:
            if self._con is not None:
                await self._pool.release(self._con)
                self._con = None


class UnitOfWorkFactory:
    """A tiny callable that hands out fresh units of work bound to the pool."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    def __call__(self) -> UnitOfWork:
        return PostgresUnitOfWork(self._pool)


async def connect(dsn: str) -> asyncpg.Pool:
    pool: asyncpg.Pool = await asyncpg.create_pool(dsn, min_size=2, max_size=8)
    async with pool.acquire() as con:
        await con.execute("DROP TABLE IF EXISTS orders, outbox")
        await con.execute(
            "CREATE TABLE orders (id text PRIMARY KEY, customer text NOT NULL, "
            "amount_cents int NOT NULL)"
        )
        await con.execute(
            "CREATE TABLE outbox (seq bigserial PRIMARY KEY, event_id text UNIQUE NOT NULL, "
            "aggregate_id text NOT NULL, type text NOT NULL, payload text NOT NULL, "
            "sent bool NOT NULL DEFAULT false)"
        )
    return pool

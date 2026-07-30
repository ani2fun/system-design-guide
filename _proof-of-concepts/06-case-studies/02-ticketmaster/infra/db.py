"""Postgres pool, schema bootstrap, and seat seeding (infrastructure)."""

from __future__ import annotations

from pathlib import Path

import asyncpg

_SCHEMA = (Path(__file__).resolve().parent.parent / "sql" / "schema.sql").read_text()


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool: asyncpg.Pool = await asyncpg.create_pool(dsn, min_size=2, max_size=20)
    async with pool.acquire() as con:
        await con.execute(_SCHEMA)
    return pool


async def seed_seats(pool: asyncpg.Pool, event_id: str, seat_count: int) -> None:
    async with pool.acquire() as con:
        await con.executemany(
            "INSERT INTO seats (seat_id, event_id) VALUES ($1, $2) "
            "ON CONFLICT (seat_id) DO NOTHING",
            [(f"{event_id}:S{i}", event_id) for i in range(1, seat_count + 1)],
        )

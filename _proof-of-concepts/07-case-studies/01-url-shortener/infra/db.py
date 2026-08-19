"""Postgres connection pool + idempotent schema/seed bootstrap (infrastructure)."""

from __future__ import annotations

from pathlib import Path

import asyncpg

_SCHEMA = (Path(__file__).resolve().parent.parent / "sql" / "schema.sql").read_text()


async def create_pool(dsn: str, counter_start: int) -> asyncpg.Pool:
    pool: asyncpg.Pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    async with pool.acquire() as con:
        await con.execute(_SCHEMA)
        await con.execute(
            "INSERT INTO id_range_allocator (name, next_value) VALUES ('global', $1) "
            "ON CONFLICT (name) DO NOTHING",
            counter_start,
        )
    return pool

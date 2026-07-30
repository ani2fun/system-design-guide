"""Postgres pool + schema bootstrap (shared by API and worker)."""

from __future__ import annotations

from pathlib import Path

import asyncpg

_SCHEMA = (Path(__file__).resolve().parent.parent / "sql" / "schema.sql").read_text()


async def create_pool(dsn: str, ensure_schema: bool = True) -> asyncpg.Pool:
    pool: asyncpg.Pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    if ensure_schema:  # the API owns schema creation; the worker waits for the API
        async with pool.acquire() as con:
            await con.execute(_SCHEMA)
    return pool

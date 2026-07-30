"""Postgres pool + schema (infrastructure)."""

from __future__ import annotations

import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool: asyncpg.Pool = await asyncpg.create_pool(dsn, min_size=2, max_size=20)
    async with pool.acquire() as con:
        await con.execute(
            "CREATE TABLE IF NOT EXISTS trips ("
            "  id BIGSERIAL PRIMARY KEY,"
            "  request_id TEXT UNIQUE NOT NULL,"   # exactly-once per ride request
            "  driver_id TEXT NOT NULL,"
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
    return pool

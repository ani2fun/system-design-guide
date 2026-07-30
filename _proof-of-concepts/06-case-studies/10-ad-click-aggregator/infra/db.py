"""Postgres pool + schema (infrastructure)."""

from __future__ import annotations

import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool: asyncpg.Pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    async with pool.acquire() as con:
        await con.execute("CREATE TABLE IF NOT EXISTS seen (impression_id TEXT PRIMARY KEY)")
        await con.execute(
            "CREATE TABLE IF NOT EXISTS aggregates ("
            "  ad_id TEXT NOT NULL,"
            "  window_start_ms BIGINT NOT NULL,"
            "  count INT NOT NULL,"
            "  PRIMARY KEY (ad_id, window_start_ms))"
        )
    return pool

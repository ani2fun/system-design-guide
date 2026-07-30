"""Postgres pool + schema (infrastructure)."""

from __future__ import annotations

import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool: asyncpg.Pool = await asyncpg.create_pool(dsn, min_size=2, max_size=20)
    async with pool.acquire() as con:
        await con.execute(
            "CREATE TABLE IF NOT EXISTS executions ("
            "  execution_id TEXT PRIMARY KEY,"
            "  due_ms BIGINT NOT NULL,"
            "  status TEXT NOT NULL DEFAULT 'pending',"
            "  worker TEXT,"
            "  visibility_deadline_ms BIGINT,"
            "  epoch INT)"
        )
    return pool

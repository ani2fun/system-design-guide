"""Postgres pool + schema for the content-addressed store (infrastructure)."""

from __future__ import annotations

import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool: asyncpg.Pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    async with pool.acquire() as con:
        # chunks: key = content hash (immutable, deduped). files: current manifest.
        await con.execute("CREATE TABLE IF NOT EXISTS chunks (hash TEXT PRIMARY KEY, data BYTEA NOT NULL)")
        await con.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, hashes TEXT[] NOT NULL)")
    return pool

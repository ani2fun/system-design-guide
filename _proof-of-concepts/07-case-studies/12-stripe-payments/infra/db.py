"""Postgres pool + schema (infrastructure)."""

from __future__ import annotations

import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool: asyncpg.Pool = await asyncpg.create_pool(dsn, min_size=2, max_size=20)
    async with pool.acquire() as con:
        await con.execute(
            "CREATE TABLE IF NOT EXISTS idempotency (key TEXT PRIMARY KEY, result JSONB)"
        )
        await con.execute(
            "CREATE TABLE IF NOT EXISTS payments ("
            "  id BIGSERIAL PRIMARY KEY, merchant TEXT NOT NULL, amount INT NOT NULL, state TEXT NOT NULL)"
        )
        await con.execute(
            "CREATE TABLE IF NOT EXISTS ledger ("
            "  id BIGSERIAL PRIMARY KEY, account TEXT NOT NULL, amount INT NOT NULL,"
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
    return pool

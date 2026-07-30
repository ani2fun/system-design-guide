"""Postgres pool + deterministic seed of the demo table (infrastructure)."""

from __future__ import annotations

import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool: asyncpg.Pool = await asyncpg.create_pool(dsn, min_size=2, max_size=6)
    return pool


async def seed(pool: asyncpg.Pool, rows: int) -> None:
    """Rebuild `events` with `rows` rows. `email` is unique (single-row lookups →
    clean Index Scan); `status` is skewed (~90% 'ok') to demo selectivity.
    VACUUM sets the visibility map, which index-only scans require."""
    async with pool.acquire() as con:
        await con.execute("DROP TABLE IF EXISTS events")
        await con.execute(
            "CREATE TABLE events ("
            "  id bigint PRIMARY KEY,"
            "  email text NOT NULL,"
            "  status text NOT NULL,"
            "  amount int NOT NULL,"
            "  created_at timestamptz NOT NULL)"
        )
        await con.execute(
            "INSERT INTO events (id, email, status, amount, created_at) "
            "SELECT g, 'user' || lpad(g::text, 8, '0'), "
            "       CASE WHEN g % 10 = 0 THEN 'failed' ELSE 'ok' END, "
            "       (g % 1000)::int, now() - (g || ' seconds')::interval "
            "FROM generate_series(1, $1) g",
            rows,
        )
        await con.execute("VACUUM (ANALYZE) events")  # stats + visibility map

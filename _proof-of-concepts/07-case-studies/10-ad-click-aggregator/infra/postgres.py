"""Postgres adapters — dedup store + aggregate sink (infrastructure)."""

from __future__ import annotations

import asyncpg

from domain.model import WindowCount
from domain.ports import AggregateSink, DedupStore


class PostgresDedupStore(DedupStore):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def first_time(self, impression_id: str) -> bool:
        row = await self._pool.fetchval(
            "INSERT INTO seen (impression_id) VALUES ($1) ON CONFLICT DO NOTHING RETURNING impression_id",
            impression_id,
        )
        return row is not None  # a row means it was newly inserted


class PostgresAggregateSink(AggregateSink):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert(self, ad_id: str, window_start_ms: int, count: int) -> None:
        await self._pool.execute(
            "INSERT INTO aggregates (ad_id, window_start_ms, count) VALUES ($1, $2, $3) "
            "ON CONFLICT (ad_id, window_start_ms) DO UPDATE SET count = EXCLUDED.count",
            ad_id,
            window_start_ms,
            count,
        )

    async def get(self, ad_id: str) -> list[WindowCount]:
        rows = await self._pool.fetch(
            "SELECT window_start_ms, count FROM aggregates WHERE ad_id = $1 ORDER BY window_start_ms",
            ad_id,
        )
        return [WindowCount(ad_id, int(r["window_start_ms"]), int(r["count"])) for r in rows]

"""Postgres adapter — the TripStore port (infrastructure).

The UNIQUE(request_id) constraint is what makes trip creation exactly-once.
"""

from __future__ import annotations

import asyncpg

from domain.ports import TripStore


class PostgresTripStore(TripStore):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, request_id: str) -> tuple[int, str] | None:
        row = await self._pool.fetchrow(
            "SELECT id, driver_id FROM trips WHERE request_id = $1", request_id
        )
        return (int(row["id"]), str(row["driver_id"])) if row is not None else None

    async def create(self, request_id: str, driver_id: str) -> tuple[int, bool]:
        new_id: int | None = await self._pool.fetchval(
            "INSERT INTO trips (request_id, driver_id) VALUES ($1, $2) "
            "ON CONFLICT (request_id) DO NOTHING RETURNING id",
            request_id,
            driver_id,
        )
        if new_id is not None:
            return int(new_id), True
        existing = await self.get(request_id)
        assert existing is not None
        return existing[0], False

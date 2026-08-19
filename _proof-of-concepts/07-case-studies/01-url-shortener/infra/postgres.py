"""Postgres adapters — implement the persistence ports (infrastructure).

These are the only place asyncpg is imported. They translate driver errors into
domain errors (UniqueViolationError → DuplicateCodeError), so the domain stays
driver-agnostic.
"""

from __future__ import annotations

import asyncpg

from domain.errors import DuplicateCodeError
from domain.model import Link
from domain.ports import LinkRepository, RangeAllocator


class PostgresLinkRepository(LinkRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def add(self, link: Link) -> None:
        try:
            await self._pool.execute(
                "INSERT INTO links (code, long_url) VALUES ($1, $2)",
                link.code,
                link.long_url.value,
            )
        except asyncpg.UniqueViolationError as exc:
            raise DuplicateCodeError(link.code) from exc

    async def get(self, code: str) -> str | None:
        url: str | None = await self._pool.fetchval(
            "SELECT long_url FROM links WHERE code = $1", code
        )
        return url


class PostgresRangeAllocator(RangeAllocator):
    def __init__(self, pool: asyncpg.Pool, name: str = "global") -> None:
        self._pool = pool
        self._name = name

    async def allocate(self, batch: int) -> int:
        high: int = await self._pool.fetchval(
            "UPDATE id_range_allocator SET next_value = next_value + $1 "
            "WHERE name = $2 RETURNING next_value",
            batch,
            self._name,
        )
        return high

"""Ports the stream aggregator depends on (Dependency Inversion).

`DedupStore` (impression-id membership) and `AggregateSink` (the OLAP upsert
target). The domain never imports asyncpg.
"""

from __future__ import annotations

import abc

from domain.model import WindowCount


class DedupStore(abc.ABC):
    @abc.abstractmethod
    async def first_time(self, impression_id: str) -> bool:
        """True iff this impression id is being seen for the first time."""


class AggregateSink(abc.ABC):
    @abc.abstractmethod
    async def upsert(self, ad_id: str, window_start_ms: int, count: int) -> None:
        """Idempotent write keyed by (ad, window) — re-emitting overwrites."""

    @abc.abstractmethod
    async def get(self, ad_id: str) -> list[WindowCount]:
        """Window counts for an ad, oldest window first."""

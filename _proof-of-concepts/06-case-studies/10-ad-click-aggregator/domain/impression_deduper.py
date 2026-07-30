"""ImpressionDeduper — collapse duplicate clicks (C4 code element).

A redelivery from the log or a viewer's double-click carry the same signed
impression id; only the first is counted.
"""

from __future__ import annotations

from domain.ports import DedupStore


class ImpressionDeduper:
    def __init__(self, dedup: DedupStore) -> None:
        self._dedup = dedup

    async def is_duplicate(self, impression_id: str) -> bool:
        return not await self._dedup.first_time(impression_id)

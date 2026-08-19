"""RangeLease — leases disjoint counter ranges from a RangeAllocator (C4 code element).

Depends on the `RangeAllocator` port, not on Postgres. Leasing a batch is one
atomic fetch-and-add; ids are then served locally until the range is exhausted.
A crash loses the in-memory tail of the range — those ids are never reissued, so
codes are unique by construction (gaps, never duplicates).
"""

from __future__ import annotations

import asyncio

from domain.ports import RangeAllocator


class RangeLease:
    def __init__(self, allocator: RangeAllocator, batch: int = 1000) -> None:
        self._allocator = allocator
        self._batch = batch
        self._next = 0
        self._end = 0
        self._lock = asyncio.Lock()
        self.ranges_leased = 0
        self.ids_issued = 0

    async def next_id(self) -> int:
        async with self._lock:
            if self._next >= self._end:
                high = await self._allocator.allocate(self._batch)
                self._end = high
                self._next = high - self._batch
                self.ranges_leased += 1
            value = self._next
            self._next += 1
            self.ids_issued += 1
            return value

    def status(self) -> dict[str, int]:
        return {
            "batch": self._batch,
            "current_id": self._next,
            "range_end": self._end,
            "remaining_in_range": max(0, self._end - self._next),
            "ranges_leased": self.ranges_leased,
            "ids_issued": self.ids_issued,
        }

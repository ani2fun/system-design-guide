"""LeaderLease — hold the lease, carry the epoch as a fencing token (C4 code element).

Acquiring leadership mints a NEW monotonic epoch. A paused ex-leader that wakes
up still holds an old epoch; downstream fencing rejects it — the double-fire
guard.
"""

from __future__ import annotations

from domain.ports import Coordinator


class LeaderLease:
    def __init__(self, coord: Coordinator, node: str, ttl_ms: int = 3000) -> None:
        self._coord = coord
        self._node = node
        self._ttl = ttl_ms
        self.epoch: int | None = None

    async def acquire(self) -> bool:
        self.epoch = await self._coord.acquire(self._node, self._ttl)
        return self.epoch is not None

    @property
    def is_leader(self) -> bool:
        return self.epoch is not None

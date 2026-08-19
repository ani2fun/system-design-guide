"""SeatHoldService — per-seat TTL holds (C4 code element).

Depends on the SeatHoldStore port, not on Redis. A hold is the checkout's
admission ticket: acquire is atomic (only one holder wins) and expires on its
own, so a crashed checkout releases the seat automatically.
"""

from __future__ import annotations

from domain.ports import SeatHoldStore


class SeatHoldService:
    def __init__(self, store: SeatHoldStore, ttl_ms: int = 120_000) -> None:
        self._store = store
        self._ttl = ttl_ms
        self.acquired = 0
        self.rejected = 0

    async def acquire(self, seat_id: str, holder: str) -> bool:
        ok = await self._store.acquire(seat_id, holder, self._ttl)
        if ok:
            self.acquired += 1
        else:
            self.rejected += 1
        return ok

    async def holder(self, seat_id: str) -> str | None:
        return await self._store.holder(seat_id)

    async def release(self, seat_id: str, holder: str) -> None:
        await self._store.release(seat_id, holder)

    def status(self) -> dict[str, int]:
        return {"holds_acquired": self.acquired, "holds_rejected": self.rejected}

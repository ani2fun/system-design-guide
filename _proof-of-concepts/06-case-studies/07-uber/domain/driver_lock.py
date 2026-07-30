"""DriverLock — the offer-window lock, one offer at a time (C4 code element).

`SET NX PX` per driver: only one matching flow can hold a driver's offer lock,
and TTL expiry (not cleanup code) releases a crashed flow — the Ticketmaster
seat hold wearing a different hat.
"""

from __future__ import annotations

from domain.ports import LockStore


class DriverLock:
    def __init__(self, locks: LockStore, ttl_ms: int = 15_000) -> None:
        self._locks = locks
        self._ttl = ttl_ms

    async def acquire(self, driver_id: str) -> bool:
        return await self._locks.acquire(driver_id, self._ttl)

    async def release(self, driver_id: str) -> None:
        await self._locks.release(driver_id)

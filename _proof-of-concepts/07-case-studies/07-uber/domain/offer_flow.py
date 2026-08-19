"""OfferFlow — offer → accept | expire → next candidate (C4 code element).

Walks nearby candidates, locking each before offering so no driver is offered to
two riders at once. The first lockable driver is assigned and a trip is created
exactly once per request (the trip store's unique constraint is the final
arbiter). A retry of the same request returns the same trip — idempotent.
"""

from __future__ import annotations

from domain.driver_lock import DriverLock
from domain.model import MatchResult
from domain.nearby_driver_query import NearbyDriverQuery
from domain.ports import TripStore


class OfferFlow:
    def __init__(
        self,
        nearby: NearbyDriverQuery,
        lock: DriverLock,
        trips: TripStore,
        radius_km: float = 5.0,
        max_candidates: int = 10,
    ) -> None:
        self._nearby = nearby
        self._lock = lock
        self._trips = trips
        self._radius = radius_km
        self._max = max_candidates

    async def match(self, request_id: str, lon: float, lat: float) -> MatchResult | None:
        existing = await self._trips.get(request_id)
        if existing is not None:
            trip_id, driver_id = existing
            return MatchResult(request_id, driver_id, trip_id)  # idempotent

        for driver_id in await self._nearby.query(lon, lat, self._radius, self._max):
            if not await self._lock.acquire(driver_id):
                continue  # driver already being offered elsewhere → next candidate
            trip_id, created = await self._trips.create(request_id, driver_id)
            if created:
                return MatchResult(request_id, driver_id, trip_id)
            # a concurrent flow already made this request's trip; keep that one.
            await self._lock.release(driver_id)
            again = await self._trips.get(request_id)
            return None if again is None else MatchResult(request_id, again[1], again[0])

        return None  # no available driver nearby

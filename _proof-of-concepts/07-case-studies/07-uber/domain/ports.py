"""Ports — the abstractions the matching domain depends on (Dependency Inversion).

`GeoIndex` (nearby drivers), `LockStore` (per-driver offer lock), `TripStore`
(exactly-once trip). The domain never imports redis or asyncpg.
"""

from __future__ import annotations

import abc


class GeoIndex(abc.ABC):
    @abc.abstractmethod
    async def add_driver(self, driver_id: str, lon: float, lat: float) -> None: ...

    @abc.abstractmethod
    async def nearby(self, lon: float, lat: float, radius_km: float, count: int) -> list[str]:
        """Driver ids within radius, nearest first."""


class LockStore(abc.ABC):
    @abc.abstractmethod
    async def acquire(self, driver_id: str, ttl_ms: int) -> bool:
        """SET NX PX — True iff this caller now holds the offer lock for the driver."""

    @abc.abstractmethod
    async def release(self, driver_id: str) -> None: ...


class TripStore(abc.ABC):
    @abc.abstractmethod
    async def get(self, request_id: str) -> tuple[int, str] | None:
        """(trip_id, driver_id) for a request, or None."""

    @abc.abstractmethod
    async def create(self, request_id: str, driver_id: str) -> tuple[int, bool]:
        """Insert a trip; returns (trip_id, created). created=False ⇒ the request
        already had a trip (unique constraint) — exactly-once."""

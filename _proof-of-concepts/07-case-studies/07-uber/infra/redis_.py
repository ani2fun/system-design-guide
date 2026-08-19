"""Redis adapters — geo index + per-driver offer locks (infrastructure)."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, cast

from redis.asyncio import Redis

from domain.ports import GeoIndex, LockStore


class RedisGeoIndex(GeoIndex):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def add_driver(self, driver_id: str, lon: float, lat: float) -> None:
        await cast("Awaitable[int]", self._redis.geoadd("drivers", (lon, lat, driver_id)))

    async def nearby(self, lon: float, lat: float, radius_km: float, count: int) -> list[str]:
        result = await cast(
            "Awaitable[list[Any]]",
            self._redis.geosearch(
                "drivers",
                longitude=lon,
                latitude=lat,
                radius=radius_km,
                unit="km",
                sort="ASC",
                count=count,
            ),
        )
        return [str(member) for member in result]


class RedisLockStore(LockStore):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def acquire(self, driver_id: str, ttl_ms: int) -> bool:
        ok = await self._redis.set(f"lock:{driver_id}", "1", nx=True, px=ttl_ms)
        return bool(ok)

    async def release(self, driver_id: str) -> None:
        await cast("Awaitable[int]", self._redis.delete(f"lock:{driver_id}"))

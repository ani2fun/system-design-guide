"""Redis adapter — the Coordinator port: leader lease + monotonic epoch."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

from domain.ports import Coordinator


class RedisCoordinator(Coordinator):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def acquire(self, node: str, ttl_ms: int) -> int | None:
        got = await self._redis.set("lease", node, nx=True, px=ttl_ms)
        if not got:
            return None
        epoch = await cast("Awaitable[int]", self._redis.incr("epoch"))
        return int(epoch)

    async def current_epoch(self) -> int:
        value: str | None = await cast("Awaitable[str | None]", self._redis.get("epoch"))
        return int(value) if value is not None else 0

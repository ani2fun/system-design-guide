"""Redis adapters — seen set, per-host frontier queues, host gate (infrastructure)."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

from domain.ports import Frontier, HostGate, SeenStore


class RedisSeenStore(SeenStore):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def add_if_new(self, key: str) -> bool:
        return bool(await cast("Awaitable[int]", self._redis.sadd("seen", key)))


class RedisFrontier(Frontier):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def enqueue(self, host: str, url: str) -> None:
        await cast("Awaitable[int]", self._redis.rpush(f"q:{host}", url))
        await cast("Awaitable[int]", self._redis.sadd("hosts", host))

    async def hosts(self) -> list[str]:
        members = await cast("Awaitable[set[str]]", self._redis.smembers("hosts"))
        return list(members)

    async def pop(self, host: str) -> str | None:
        url: str | None = await cast("Awaitable[str | None]", self._redis.lpop(f"q:{host}"))
        if await self.size(host) == 0:
            await cast("Awaitable[int]", self._redis.srem("hosts", host))
        return url

    async def size(self, host: str) -> int:
        return await cast("Awaitable[int]", self._redis.llen(f"q:{host}"))


class RedisHostGate(HostGate):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def try_open(self, host: str, interval_ms: int) -> bool:
        ok = await self._redis.set(f"gate:{host}", "1", nx=True, px=interval_ms)
        return bool(ok)

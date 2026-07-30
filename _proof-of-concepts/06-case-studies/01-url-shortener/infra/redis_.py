"""Redis adapters — implement the cache and click-publisher ports (infrastructure).

The only place redis is imported. RedisClickPublisher owns the fire-and-forget
semantics: `publish` schedules the stream write and returns immediately, so a
redirect never waits on the analytics write.
"""

from __future__ import annotations

import asyncio
import time

from redis.asyncio import Redis

from domain.ports import ClickPublisher, RedirectCache


class RedisRedirectCache(RedirectCache):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, code: str) -> str | None:
        url: str | None = await self._redis.get(code)
        return url

    async def set(self, code: str, url: str, ttl: int) -> None:
        await self._redis.set(code, url, ex=ttl)


class RedisClickPublisher(ClickPublisher):
    def __init__(self, redis: Redis, stream: str = "clicks") -> None:
        self._redis = redis
        self._stream = stream
        self.emitted = 0

    async def publish(self, code: str) -> None:
        # fire-and-forget: schedule, don't await the write on the redirect path.
        asyncio.create_task(self._xadd(code))

    async def _xadd(self, code: str) -> None:
        try:
            await self._redis.xadd(
                self._stream,
                {"code": code, "ts": str(time.time())},
                maxlen=100_000,
                approximate=True,
            )
            self.emitted += 1
        except Exception:  # noqa: BLE001 - analytics is best-effort
            pass

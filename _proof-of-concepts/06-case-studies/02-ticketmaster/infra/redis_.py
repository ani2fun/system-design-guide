"""Redis adapter — the SeatHoldStore port (infrastructure).

Holds are `SET hold:{seat} holder NX PX ttl` (atomic, self-expiring); release is
a compare-and-delete Lua script so a process only frees a hold it still owns.
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

from domain.ports import SeatHoldStore

_RELEASE_LUA = (
    "if redis.call('get', KEYS[1]) == ARGV[1] "
    "then return redis.call('del', KEYS[1]) else return 0 end"
)


class RedisSeatHoldStore(SeatHoldStore):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def _key(seat_id: str) -> str:
        return f"hold:{seat_id}"

    async def acquire(self, seat_id: str, holder: str, ttl_ms: int) -> bool:
        ok = await self._redis.set(self._key(seat_id), holder, nx=True, px=ttl_ms)
        return bool(ok)

    async def holder(self, seat_id: str) -> str | None:
        value: str | None = await self._redis.get(self._key(seat_id))
        return value

    async def release(self, seat_id: str, holder: str) -> None:
        # redis-py types the sync+async API as one union; on the async client the
        # call is always awaitable, so narrow it explicitly.
        await cast("Awaitable[object]", self._redis.eval(_RELEASE_LUA, 1, self._key(seat_id), holder))

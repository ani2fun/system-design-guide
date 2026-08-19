"""Redis adapters — the TimelineCache and FanoutQueue ports (infrastructure).

The only place redis is imported. redis-py types its sync+async API as one
union, so async calls are narrowed with `cast` where the union confuses mypy.
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

from domain.model import PostEvent
from domain.ports import FanoutQueue, TimelineCache


class RedisTimelineCache(TimelineCache):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def add_to_many(self, user_ids: list[int], post_id: int, cap: int) -> None:
        pipe = self._redis.pipeline()
        for uid in user_ids:
            key = f"timeline:{uid}"
            pipe.zadd(key, {str(post_id): post_id})          # idempotent
            pipe.zremrangebyrank(key, 0, -(cap + 1))          # cap to newest N
        await pipe.execute()

    async def recent_ids(self, user_id: int, limit: int) -> list[int]:
        raw = await cast(
            "Awaitable[list[str]]", self._redis.zrevrange(f"timeline:{user_id}", 0, limit - 1)
        )
        return [int(x) for x in raw]


class RedisFanoutQueue(FanoutQueue):
    def __init__(self, redis: Redis, stream: str, group: str, consumer: str = "w1") -> None:
        self._redis = redis
        self._stream = stream
        self._group = group
        self._consumer = consumer

    async def publish(self, post_id: int, author_id: int) -> None:
        await self._redis.xadd(self._stream, {"post_id": str(post_id), "author_id": str(author_id)})

    async def ensure_group(self) -> None:
        try:
            await self._redis.xgroup_create(self._stream, self._group, id="0", mkstream=True)
        except Exception as exc:  # noqa: BLE001 - redis raises a generic error on BUSYGROUP
            if "BUSYGROUP" not in str(exc):
                raise

    async def poll(self, count: int, block_ms: int) -> list[PostEvent]:
        resp = await cast(
            "Awaitable[list[tuple[str, list[tuple[str, dict[str, str]]]]]]",
            self._redis.xreadgroup(
                self._group, self._consumer, {self._stream: ">"}, count=count, block=block_ms
            ),
        )
        events: list[PostEvent] = []
        for _stream, entries in resp or []:
            for msg_id, fields in entries:
                events.append(
                    PostEvent(
                        msg_id=msg_id,
                        post_id=int(fields["post_id"]),
                        author_id=int(fields["author_id"]),
                    )
                )
        return events

    async def ack(self, msg_id: str) -> None:
        await cast("Awaitable[int]", self._redis.xack(self._stream, self._group, msg_id))

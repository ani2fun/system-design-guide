"""Redis adapters — presence, inbox, and the cross-server bus (infrastructure).

The only place redis is imported. `RedisMessageBus.listen` is a concrete helper
(not part of the port) the app uses to run its subscriber loop.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable
from typing import Any, cast

from redis.asyncio import Redis

from domain.model import Message
from domain.ports import InboxStore, MessageBus, PresenceStore


class RedisPresenceStore(PresenceStore):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def set_online(self, user: str, server_id: str) -> None:
        await cast("Awaitable[int]", self._redis.hset("presence", user, server_id))

    async def set_offline(self, user: str) -> None:
        await cast("Awaitable[int]", self._redis.hdel("presence", user))

    async def server_of(self, user: str) -> str | None:
        value: str | None = await cast("Awaitable[Any]", self._redis.hget("presence", user))
        return value


class RedisInboxStore(InboxStore):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def _key(user: str) -> str:
        return f"inbox:{user}"

    async def add(self, user: str, message: Message) -> None:
        await cast("Awaitable[int]", self._redis.hset(self._key(user), message.id, message.to_json()))

    async def ack(self, user: str, message_id: str) -> None:
        await cast("Awaitable[int]", self._redis.hdel(self._key(user), message_id))

    async def drain(self, user: str) -> list[Message]:
        raw: dict[str, str] = await cast("Awaitable[dict[str, str]]", self._redis.hgetall(self._key(user)))
        return [Message.from_json(raw[k]) for k in sorted(raw)]


class RedisMessageBus(MessageBus):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def publish(self, channel: str, payload: str) -> None:
        await cast("Awaitable[int]", self._redis.publish(channel, payload))

    async def listen(self, channel: str) -> AsyncIterator[str]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield str(message["data"])

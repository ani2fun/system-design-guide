"""Redis adapter — atomic Lua execution (infrastructure)."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, cast

from redis.asyncio import Redis

from domain.ports import ScriptRunner


class RedisScriptRunner(ScriptRunner):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def eval(self, script: str, keys: list[str], args: list[str]) -> list[int]:
        reply = await cast(
            "Awaitable[list[Any]]", self._redis.eval(script, len(keys), *keys, *args)
        )
        return [int(x) for x in reply]

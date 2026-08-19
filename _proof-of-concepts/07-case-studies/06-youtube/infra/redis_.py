"""Redis adapters — rendition store + metadata store (infrastructure)."""

from __future__ import annotations

import json
from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

from pipeline.ports import MetadataStore, RenditionStore


class RedisRenditionStore(RenditionStore):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def exists(self, key: str) -> bool:
        return bool(await cast("Awaitable[int]", self._redis.hexists("renditions", key)))

    async def put(self, key: str, data: bytes) -> None:
        # latin-1 is a total, lossless byte↔str map (the decode_responses client wants str)
        await cast("Awaitable[int]", self._redis.hset("renditions", key, data.decode("latin-1")))


class RedisMetadataStore(MetadataStore):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def set_state(self, video: str, state: str) -> None:
        await cast("Awaitable[int]", self._redis.hset(f"video:{video}", "state", state))

    async def get_state(self, video: str) -> str:
        value: str | None = await cast("Awaitable[str | None]", self._redis.hget(f"video:{video}", "state"))
        return value or "unknown"

    async def put_manifest(self, video: str, rendition: str, keys: list[str]) -> None:
        await cast("Awaitable[int]", self._redis.hset(f"manifest:{video}", rendition, json.dumps(keys)))

    async def manifests(self, video: str) -> dict[str, list[str]]:
        raw: dict[str, str] = await cast("Awaitable[dict[str, str]]", self._redis.hgetall(f"manifest:{video}"))
        return {rendition: list(json.loads(payload)) for rendition, payload in raw.items()}

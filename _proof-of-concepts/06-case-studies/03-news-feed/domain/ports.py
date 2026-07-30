"""Ports — the abstractions the feed domain depends on (Dependency Inversion).

Explicit `abc.ABC` interfaces implemented by the infra adapters. The domain
(read path in the API, fan-out pipeline in the worker) imports only these — never
asyncpg or redis.
"""

from __future__ import annotations

import abc

from domain.model import Post, PostEvent


class PostRepository(abc.ABC):
    """System of record for posts."""

    @abc.abstractmethod
    async def add(self, author_id: int, content: str) -> int:
        """Insert a post, return its id."""

    @abc.abstractmethod
    async def hydrate(self, ids: list[int]) -> list[Post]:
        """Fetch post bodies for a set of ids (order not guaranteed)."""


class FollowGraph(abc.ABC):
    """The follower/followee edges."""

    @abc.abstractmethod
    async def add_follow(self, follower_id: int, followee_id: int) -> None: ...

    @abc.abstractmethod
    async def followers(self, author_id: int) -> list[int]: ...

    @abc.abstractmethod
    async def follower_count(self, author_id: int) -> int: ...


class FeedQueries(abc.ABC):
    """Read-model queries that span posts + graph (celebrity read path)."""

    @abc.abstractmethod
    async def celebrity_recent_post_ids(self, user_id: int, threshold: int, limit: int) -> list[int]:
        """Recent post ids of the celebrity accounts (>= threshold followers) this user follows."""

    @abc.abstractmethod
    async def celebrities(self, threshold: int) -> list[tuple[int, int]]:
        """(author_id, follower_count) for every author at/over the threshold."""


class TimelineCache(abc.ABC):
    """Per-user materialized home timelines (post ids only)."""

    @abc.abstractmethod
    async def add_to_many(self, user_ids: list[int], post_id: int, cap: int) -> None:
        """Idempotently insert a post id into each user's timeline, capped to `cap` newest."""

    @abc.abstractmethod
    async def recent_ids(self, user_id: int, limit: int) -> list[int]: ...


class FanoutQueue(abc.ABC):
    """The async boundary: post events in, at-least-once delivery to the worker."""

    @abc.abstractmethod
    async def publish(self, post_id: int, author_id: int) -> None: ...

    @abc.abstractmethod
    async def ensure_group(self) -> None: ...

    @abc.abstractmethod
    async def poll(self, count: int, block_ms: int) -> list[PostEvent]: ...

    @abc.abstractmethod
    async def ack(self, msg_id: str) -> None: ...

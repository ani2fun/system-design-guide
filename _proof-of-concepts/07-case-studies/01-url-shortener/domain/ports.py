"""Ports — the abstractions the domain depends on (Dependency Inversion).

These are explicit `abc.ABC` interfaces: an infrastructure adapter must inherit
and implement every abstract method, or instantiating it raises `TypeError` at
runtime. mypy also checks the signatures statically. The domain imports only
these ports — never asyncpg or redis.
"""

from __future__ import annotations

import abc

from domain.model import Link


class LinkRepository(abc.ABC):
    """Persistence of the code → URL mapping (system of record)."""

    @abc.abstractmethod
    async def add(self, link: Link) -> None:
        """Persist a new link. Raise DuplicateCodeError if the code exists."""

    @abc.abstractmethod
    async def get(self, code: str) -> str | None:
        """Return the long URL for a code, or None if unknown."""


class RangeAllocator(abc.ABC):
    """Hands out disjoint counter ranges via atomic fetch-and-add."""

    @abc.abstractmethod
    async def allocate(self, batch: int) -> int:
        """Advance the global counter by `batch` and return the new high mark."""


class RedirectCache(abc.ABC):
    """Hot code → URL cache in front of the repository."""

    @abc.abstractmethod
    async def get(self, code: str) -> str | None: ...

    @abc.abstractmethod
    async def set(self, code: str, url: str, ttl: int) -> None: ...


class ClickPublisher(abc.ABC):
    """Emits click events for the async analytics pipeline."""

    @abc.abstractmethod
    async def publish(self, code: str) -> None:
        """Record a click. Delivery is best-effort and must not block the redirect."""

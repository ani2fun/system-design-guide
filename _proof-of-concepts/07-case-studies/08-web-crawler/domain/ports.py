"""Ports the frontier depends on (Dependency Inversion).

`SeenStore` (URL-seen membership), `Frontier` (per-host FIFO queues), `HostGate`
(per-host politeness rate gate). The domain never imports redis.
"""

from __future__ import annotations

import abc


class SeenStore(abc.ABC):
    @abc.abstractmethod
    async def add_if_new(self, key: str) -> bool:
        """True iff `key` was not already present (and is now recorded)."""


class Frontier(abc.ABC):
    @abc.abstractmethod
    async def enqueue(self, host: str, url: str) -> None: ...

    @abc.abstractmethod
    async def hosts(self) -> list[str]:
        """Hosts that currently have queued URLs."""

    @abc.abstractmethod
    async def pop(self, host: str) -> str | None: ...

    @abc.abstractmethod
    async def size(self, host: str) -> int: ...


class HostGate(abc.ABC):
    @abc.abstractmethod
    async def try_open(self, host: str, interval_ms: int) -> bool:
        """SET NX PX — True iff the host's politeness window is open (and now closed
        for interval_ms)."""

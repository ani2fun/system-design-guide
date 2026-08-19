"""Ports the scheduler + worker depend on (Dependency Inversion).

`Coordinator` (leader lease + monotonic fencing epoch) and `ExecutionStore`
(the time-bucketed executions the scheduler polls and the worker claims). The
domain imports neither redis nor asyncpg.
"""

from __future__ import annotations

import abc


class Coordinator(abc.ABC):
    @abc.abstractmethod
    async def acquire(self, node: str, ttl_ms: int) -> int | None:
        """Try to become leader. Returns a NEW monotonic epoch if acquired, else None."""

    @abc.abstractmethod
    async def current_epoch(self) -> int: ...


class ExecutionStore(abc.ABC):
    @abc.abstractmethod
    async def register(self, execution_id: str, due_ms: int) -> None: ...

    @abc.abstractmethod
    async def poll_due(self, now_ms: int, window_ms: int) -> list[str]:
        """PENDING execution ids due within [now, now+window) — a bounded range read."""

    @abc.abstractmethod
    async def stamp_epoch(self, execution_id: str, epoch: int) -> None: ...

    @abc.abstractmethod
    async def claim(self, execution_id: str, worker: str, now_ms: int, visibility_ms: int) -> bool:
        """Conditional PENDING → RUNNING (due, and not held by a live worker). True iff won."""

    @abc.abstractmethod
    async def heartbeat(self, execution_id: str, worker: str, now_ms: int, visibility_ms: int) -> bool: ...

    @abc.abstractmethod
    async def complete(self, execution_id: str, worker: str) -> bool: ...

    @abc.abstractmethod
    async def reclaim_expired(self, now_ms: int) -> int:
        """RUNNING rows whose visibility deadline passed → back to PENDING. Returns count."""

    @abc.abstractmethod
    async def status(self, execution_id: str) -> str | None: ...

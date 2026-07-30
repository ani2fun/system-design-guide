"""Heartbeat — extend the visibility timeout while running (C4 code element).

The liveness signal that turns a dead worker into a retry: keep heartbeating and
the execution stays yours; stop (crash) and its visibility deadline lapses, so
the reclaim path returns it to PENDING for a healthy worker.
"""

from __future__ import annotations

from domain.ports import ExecutionStore


class Heartbeat:
    def __init__(self, store: ExecutionStore, visibility_ms: int = 30_000) -> None:
        self._store = store
        self._visibility = visibility_ms

    async def beat(self, execution_id: str, worker: str, now_ms: int) -> bool:
        return await self._store.heartbeat(execution_id, worker, now_ms, self._visibility)

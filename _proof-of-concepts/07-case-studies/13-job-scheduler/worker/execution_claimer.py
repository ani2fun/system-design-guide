"""ExecutionClaimer — conditional claim, effectively-once (C4 code element).

A conditional PENDING → RUNNING keyed by execution id: at-least-once delivery
becomes effectively-once execution because only one worker's UPDATE matches. An
already-claimed row is a no-op.
"""

from __future__ import annotations

from domain.ports import ExecutionStore


class ExecutionClaimer:
    def __init__(self, store: ExecutionStore, visibility_ms: int = 30_000) -> None:
        self._store = store
        self._visibility = visibility_ms

    async def claim(self, execution_id: str, worker: str, now_ms: int) -> bool:
        return await self._store.claim(execution_id, worker, now_ms, self._visibility)

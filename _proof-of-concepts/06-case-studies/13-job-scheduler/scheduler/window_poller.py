"""WindowPoller — range-read the due window (C4 code element).

Bounded work per tick: read the PENDING executions due within the next window,
not a full-table scan.
"""

from __future__ import annotations

from domain.ports import ExecutionStore


class WindowPoller:
    def __init__(self, store: ExecutionStore, window_ms: int = 60_000) -> None:
        self._store = store
        self._window = window_ms

    async def poll(self, now_ms: int) -> list[str]:
        return await self._store.poll_due(now_ms, self._window)

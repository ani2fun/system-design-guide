"""Dispatcher — enqueue due executions with the current fencing epoch (C4 code element).

Only the current-epoch leader may dispatch. A stale leader (lower epoch than the
coordinator's current) is rejected — the double-fire guard in action.
"""

from __future__ import annotations

from domain.model import StaleEpochError
from domain.ports import Coordinator, ExecutionStore


class Dispatcher:
    def __init__(self, store: ExecutionStore, coord: Coordinator) -> None:
        self._store = store
        self._coord = coord

    async def dispatch(self, execution_id: str, epoch: int) -> None:
        if epoch < await self._coord.current_epoch():
            raise StaleEpochError(f"epoch {epoch} is stale")
        await self._store.stamp_epoch(execution_id, epoch)

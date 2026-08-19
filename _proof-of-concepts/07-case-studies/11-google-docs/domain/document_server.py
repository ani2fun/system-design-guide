"""DocumentServer — the ordering authority for one document.

Ties the three code elements together: transform an incoming op against the
canonical ops the client hadn't seen (OtEngine), append it, and expose presence
(SessionManager) and snapshots (Snapshotter). The in-memory op log stands in for
the persistent log store; a snapshot compacts it.
"""

from __future__ import annotations

from domain.model import Op
from domain.ot_engine import OtEngine
from domain.session_manager import SessionManager
from domain.snapshotter import Snapshotter


class StaleBaseError(Exception):
    """The client's base version predates the latest snapshot — it must reload."""


class DocumentServer:
    def __init__(self) -> None:
        self._doc = ""
        self._log: list[Op] = []
        self._snapshot_version = 0
        self._engine = OtEngine()
        self.sessions = SessionManager()
        self._snapshotter = Snapshotter(self._engine)

    @property
    def version(self) -> int:
        return self._snapshot_version + len(self._log)

    @property
    def doc(self) -> str:
        return self._doc

    def submit(self, base_version: int, op: Op) -> tuple[Op, int]:
        if base_version < self._snapshot_version:
            raise StaleBaseError(f"base {base_version} < snapshot {self._snapshot_version}")
        concurrent = self._log[base_version - self._snapshot_version :]
        transformed = self._engine.transform(op, concurrent)
        self._doc = self._engine.apply(self._doc, transformed)
        self._log.append(transformed)
        return transformed, self.version

    def snapshot(self) -> tuple[str, int]:
        # state = fold(log) is already `self._doc`; record it and compact the log.
        checkpoint = (self._doc, self.version)
        self._snapshot_version = self.version
        self._log.clear()
        return checkpoint

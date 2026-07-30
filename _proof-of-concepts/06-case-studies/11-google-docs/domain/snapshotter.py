"""Snapshotter — fold the op log into a checkpoint (C4 code element).

state = fold(ops). A cold load starts from the latest snapshot plus the tail of
the log, so it never replays op #1.
"""

from __future__ import annotations

from domain.model import Op
from domain.ot_engine import OtEngine


class Snapshotter:
    def __init__(self, engine: OtEngine) -> None:
        self._engine = engine

    def fold(self, base_doc: str, ops: list[Op]) -> str:
        doc = base_doc
        for op in ops:
            doc = self._engine.apply(doc, op)
        return doc

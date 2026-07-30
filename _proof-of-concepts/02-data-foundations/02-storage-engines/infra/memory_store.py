"""In-memory SegmentStore adapter — segments held in a list (used by tests)."""

from __future__ import annotations

from domain.model import Entry
from domain.ports import SegmentStore
from domain.sstable import SSTable


class InMemorySegmentStore(SegmentStore):
    def __init__(self) -> None:
        self._gen = 0
        self._segments: list[SSTable] = []  # oldest first internally

    def persist(self, entries: list[Entry]) -> SSTable:
        self._gen += 1
        table = SSTable(entries, self._gen)
        self._segments.append(table)
        return table

    def all(self) -> list[SSTable]:
        return list(reversed(self._segments))  # newest first

    def replace(self, inputs: list[SSTable], merged: list[Entry] | None) -> None:
        dropped = {s.generation for s in inputs}
        self._segments = [s for s in self._segments if s.generation not in dropped]
        if merged:
            self.persist(merged)

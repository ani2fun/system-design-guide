"""Ports — the abstraction the engine depends on (Dependency Inversion).

The only genuine I/O boundary in an LSM engine is *where immutable segments
live*. `SegmentStore` is an explicit `abc.ABC`: the disk adapter writes real
files, the in-memory adapter keeps a list (used by the tests). An incomplete
adapter fails at instantiation (`TypeError`); mypy checks it too.
"""

from __future__ import annotations

import abc

from domain.model import Entry
from domain.sstable import SSTable


class SegmentStore(abc.ABC):
    @abc.abstractmethod
    def persist(self, entries: list[Entry]) -> SSTable:
        """Write a new immutable segment from a sorted run; return its handle."""

    @abc.abstractmethod
    def all(self) -> list[SSTable]:
        """All live segments, NEWEST FIRST (a newer segment shadows older ones)."""

    @abc.abstractmethod
    def replace(self, inputs: list[SSTable], merged: list[Entry] | None) -> None:
        """Compaction: drop `inputs`, add one merged segment (or none if it's empty)."""

"""Disk SegmentStore adapter — each segment is a real file on disk.

Writes one file per segment (`segment-NNNN.dat`) so you can watch segments
accumulate on flush and collapse on compaction (`ls` the data dir). Tombstones
are encoded with a sentinel marker. The toy loads a segment's entries back into
the SSTable on write; a production engine would read from the file on demand.
"""

from __future__ import annotations

from pathlib import Path

from domain.model import Entry
from domain.ports import SegmentStore
from domain.sstable import SSTable

_TOMBSTONE = "\x00__tombstone__"


class DiskSegmentStore(SegmentStore):
    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)
        self._gen = 0
        self._segments: list[SSTable] = []  # oldest first internally

    def _path(self, generation: int) -> Path:
        return self._dir / f"segment-{generation:04d}.dat"

    def persist(self, entries: list[Entry]) -> SSTable:
        self._gen += 1
        lines = [f"{e.key}\t{_TOMBSTONE if e.value is None else e.value}" for e in entries]
        self._path(self._gen).write_text("\n".join(lines))
        table = SSTable(entries, self._gen)
        self._segments.append(table)
        return table

    def all(self) -> list[SSTable]:
        return list(reversed(self._segments))  # newest first

    def replace(self, inputs: list[SSTable], merged: list[Entry] | None) -> None:
        dropped = {s.generation for s in inputs}
        for generation in dropped:
            self._path(generation).unlink(missing_ok=True)
        self._segments = [s for s in self._segments if s.generation not in dropped]
        if merged:
            self.persist(merged)

    def segment_files(self) -> list[str]:
        return sorted(p.name for p in self._dir.glob("segment-*.dat"))

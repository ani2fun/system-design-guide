"""LsmEngine — the log-structured merge engine tying it together.

Writes buffer in the memtable and flush to immutable segments; reads check the
memtable then segments newest-first, using each segment's Bloom filter to skip
misses; compaction merges segments to reclaim overwrites and deletes. Depends on
the SegmentStore port + a Compactor.
"""

from __future__ import annotations

from domain.compaction import Compactor
from domain.memtable import Memtable
from domain.model import Entry
from domain.ports import SegmentStore
from domain.sstable import Lookup


class LsmEngine:
    def __init__(
        self, store: SegmentStore, memtable_threshold: int = 8, compactor: Compactor | None = None
    ) -> None:
        self._store = store
        self._threshold = memtable_threshold
        self._compactor = compactor or Compactor()
        self._memtable = Memtable()
        self.flushes = 0
        self.compactions = 0
        self.segments_read = 0

    def put(self, key: str, value: str) -> None:
        self._memtable.put(key, value)
        self._maybe_flush()

    def delete(self, key: str) -> None:
        self._memtable.put(key, None)  # tombstone
        self._maybe_flush()

    def get(self, key: str) -> str | None:
        hit = self._memtable.get(key)
        if hit is not None:
            return hit.value  # value, or None if the memtable holds a tombstone
        for segment in self._store.all():  # newest first
            self.segments_read += 1
            found = segment.get(key)
            if isinstance(found, Lookup):  # ABSENT (possibly Bloom-skipped)
                continue
            return found.value  # value, or None if the newest segment has a tombstone
        return None

    def _maybe_flush(self) -> None:
        if len(self._memtable) >= self._threshold:
            self.flush()

    def flush(self) -> None:
        if len(self._memtable) == 0:
            return
        self._store.persist(self._memtable.sorted_entries())
        self._memtable.clear()
        self.flushes += 1

    def compact(self) -> None:
        segments = self._store.all()
        if len(segments) <= 1:
            return
        merged = self._compactor.merge(segments)
        self._store.replace(segments, merged if merged else None)
        self.compactions += 1

    def scan(self) -> list[Entry]:
        latest: dict[str, Entry] = {}
        for entry in self._memtable.sorted_entries():  # memtable is newest
            latest[entry.key] = entry
        for segment in self._store.all():  # newest first
            for entry in segment.scan():
                latest.setdefault(entry.key, entry)
        return [latest[k] for k in sorted(latest) if not latest[k].is_tombstone]

    def stats(self) -> dict[str, int]:
        segments = self._store.all()
        return {
            "live_segments": len(segments),
            "total_segment_entries": sum(len(s) for s in segments),
            "flushes": self.flushes,
            "compactions": self.compactions,
            "segments_read": self.segments_read,
            "bloom_skips": sum(s.bloom_skipped for s in segments),
        }

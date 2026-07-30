"""SSTable — an immutable, sorted-string segment (C4-style building block).

Built once from a sorted run of entries, then never mutated. Carries a Bloom
filter (skip the segment on a definite miss) and a sparse index (jump close to a
key without scanning from the start). `get` distinguishes three cases: a real
value, a tombstone (found, but deleted), and absent.
"""

from __future__ import annotations

import bisect
from enum import Enum
from typing import Final

from domain.bloom import BloomFilter
from domain.model import Entry

_SPARSE_EVERY: Final = 4  # index every Nth key


class Lookup(Enum):
    ABSENT = "absent"


class SSTable:
    def __init__(self, entries: list[Entry], generation: int) -> None:
        # entries must already be sorted by key, one per key.
        self.generation = generation
        self._entries = entries
        self._keys = [e.key for e in entries]
        self._bloom = BloomFilter(expected=max(1, len(entries)))
        for key in self._keys:
            self._bloom.add(key)
        # sparse index: key → position, every Nth entry
        self._sparse: list[tuple[str, int]] = [
            (entries[i].key, i) for i in range(0, len(entries), _SPARSE_EVERY)
        ]
        self.bloom_skipped = 0

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, key: str) -> Entry | Lookup:
        if not self._bloom.might_contain(key):
            self.bloom_skipped += 1
            return Lookup.ABSENT
        # sparse index gives a start offset; scan the small window from there.
        idx = bisect.bisect_right([k for k, _ in self._sparse], key) - 1
        start = self._sparse[idx][1] if idx >= 0 else 0
        pos = bisect.bisect_left(self._keys, key, lo=start)
        if pos < len(self._keys) and self._keys[pos] == key:
            return self._entries[pos]
        return Lookup.ABSENT

    def scan(self) -> list[Entry]:
        return list(self._entries)

    def keys(self) -> list[str]:
        return list(self._keys)

"""BloomFilter — probabilistic set membership.

`item in filter` never gives a false negative (if it was added, it's found) but
may give a false positive at a tunable rate. Two filters with the same shape
merge by OR-ing their bit arrays — the union set, no re-insertion.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator


class BloomFilter:
    def __init__(self, m_bits: int, k_hashes: int) -> None:
        self._m = m_bits
        self._k = k_hashes
        self._bits = bytearray((m_bits + 7) // 8)

    def _indexes(self, item: str) -> Iterator[int]:
        data = item.encode()
        h1 = int.from_bytes(hashlib.sha256(data).digest()[:8], "big")
        h2 = int.from_bytes(hashlib.md5(data).digest()[:8], "big") | 1  # odd, non-zero
        for i in range(self._k):
            yield (h1 + i * h2) % self._m

    def add(self, item: str) -> None:
        for idx in self._indexes(item):
            self._bits[idx >> 3] |= 1 << (idx & 7)

    def __contains__(self, item: str) -> bool:
        return all(self._bits[idx >> 3] & (1 << (idx & 7)) for idx in self._indexes(item))

    def merge(self, other: BloomFilter) -> None:
        if self._m != other._m or self._k != other._k:
            raise ValueError("bloom filters must share (m, k) to merge")
        for i in range(len(self._bits)):
            self._bits[i] |= other._bits[i]

    def bytes_used(self) -> int:
        return len(self._bits)

    @staticmethod
    def optimal_k(m_bits: int, n_items: int) -> int:
        return max(1, round((m_bits / n_items) * math.log(2)))

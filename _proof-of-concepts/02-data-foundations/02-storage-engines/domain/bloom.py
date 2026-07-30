"""A tiny Bloom filter — the read-path membership test on every SSTable.

`might_contain` returns False only when the key is *definitely* absent (so the
engine can skip that segment without touching it) and True when it *might* be
present. Never a false negative; a tunable false-positive rate.
"""

from __future__ import annotations

import hashlib


class BloomFilter:
    def __init__(self, expected: int, bits_per_key: int = 10) -> None:
        self._m = max(8, expected * bits_per_key)
        self._k = max(1, round(bits_per_key * 0.693))  # ln2 · bits/key ≈ optimal
        self._bits = bytearray((self._m + 7) // 8)

    def _positions(self, key: str) -> list[int]:
        digest = hashlib.sha256(key.encode()).digest()
        h1 = int.from_bytes(digest[:8], "big")
        h2 = int.from_bytes(digest[8:16], "big") | 1
        return [(h1 + i * h2) % self._m for i in range(self._k)]

    def add(self, key: str) -> None:
        for pos in self._positions(key):
            self._bits[pos >> 3] |= 1 << (pos & 7)

    def might_contain(self, key: str) -> bool:
        return all(self._bits[pos >> 3] & (1 << (pos & 7)) for pos in self._positions(key))

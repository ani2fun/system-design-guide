"""CountMinSketch — approximate frequency of elements in a stream.

A d×w grid of counters; each element increments one counter per row. The
estimate is the minimum across rows (collisions only ever inflate a count, so
the min is the tightest bound). Two sketches of the same shape merge by adding
their grids elementwise — the combined stream's frequencies.
"""

from __future__ import annotations

import hashlib


class CountMinSketch:
    def __init__(self, width: int, depth: int) -> None:
        self._w = width
        self._d = depth
        self._counts: list[list[int]] = [[0] * width for _ in range(depth)]

    def _columns(self, item: str) -> list[int]:
        data = item.encode()
        return [
            int.from_bytes(hashlib.sha256(bytes([row]) + data).digest()[:8], "big") % self._w
            for row in range(self._d)
        ]

    def add(self, item: str, count: int = 1) -> None:
        for row, col in enumerate(self._columns(item)):
            self._counts[row][col] += count

    def estimate(self, item: str) -> int:
        return min(self._counts[row][col] for row, col in enumerate(self._columns(item)))

    def merge(self, other: CountMinSketch) -> None:
        if self._w != other._w or self._d != other._d:
            raise ValueError("sketches must share (width, depth) to merge")
        for row in range(self._d):
            self_row, other_row = self._counts[row], other._counts[row]
            for col in range(self._w):
                self_row[col] += other_row[col]

    def bytes_used(self) -> int:
        return self._w * self._d * 8  # ~8 bytes per Python-int counter slot

"""HyperLogLog — count distinct elements in a fixed, tiny amount of memory.

Every element updates one register with the rank (leading-zero count) of its
hash. Cardinality is estimated from the harmonic mean of the registers. Two HLLs
with the same precision merge by taking the per-register maximum — the union's
cardinality, with no access to the original elements.
"""

from __future__ import annotations

import hashlib
import math


class HyperLogLog:
    def __init__(self, precision: int = 14) -> None:
        self._p = precision
        self._m = 1 << precision
        self._registers = bytearray(self._m)

    @staticmethod
    def _rank(w: int, width: int) -> int:
        """1-based position of the leftmost set bit in a `width`-bit word."""
        if w == 0:
            return width + 1
        rank = 1
        mask = 1 << (width - 1)
        while mask and not (w & mask):
            rank += 1
            mask >>= 1
        return rank

    def add(self, item: str) -> None:
        h = int.from_bytes(hashlib.sha256(item.encode()).digest()[:8], "big")
        idx = h & (self._m - 1)
        rank = self._rank(h >> self._p, 64 - self._p)
        if rank > self._registers[idx]:
            self._registers[idx] = rank

    def _alpha(self) -> float:
        if self._m == 16:
            return 0.673
        if self._m == 32:
            return 0.697
        if self._m == 64:
            return 0.709
        return 0.7213 / (1 + 1.079 / self._m)

    def count(self) -> int:
        harmonic = sum(2.0 ** -r for r in self._registers)
        raw = self._alpha() * self._m * self._m / harmonic
        if raw <= 2.5 * self._m:  # small-range correction: linear counting
            zeros = self._registers.count(0)
            if zeros:
                return round(self._m * math.log(self._m / zeros))
        return round(raw)

    def merge(self, other: HyperLogLog) -> None:
        if self._p != other._p:
            raise ValueError("HLLs must share precision to merge")
        for i in range(self._m):
            if other._registers[i] > self._registers[i]:
                self._registers[i] = other._registers[i]

    def bytes_used(self) -> int:
        return self._m

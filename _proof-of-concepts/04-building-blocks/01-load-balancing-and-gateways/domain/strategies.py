"""Load-balancing strategies — each decides which backend serves a request.

All implement the explicit `LoadBalancer` ABC (Dependency Inversion): the
simulation depends only on `choose`, never on a concrete strategy. A strategy
that forgets `choose` fails at instantiation and under mypy.
"""

from __future__ import annotations

import abc
import hashlib
import random

from domain.backend import Backend


class LoadBalancer(abc.ABC):
    name: str

    @abc.abstractmethod
    def choose(self, backends: list[Backend], key: str) -> Backend:
        """Pick the backend to serve a request identified by `key`."""


class RoundRobin(LoadBalancer):
    name = "round-robin"

    def __init__(self) -> None:
        self._next = 0

    def choose(self, backends: list[Backend], key: str) -> Backend:
        b = backends[self._next % len(backends)]
        self._next += 1
        return b


class RandomChoice(LoadBalancer):
    name = "random"

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def choose(self, backends: list[Backend], key: str) -> Backend:
        return self._rng.choice(backends)


class LeastConnections(LoadBalancer):
    name = "least-connections"

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def choose(self, backends: list[Backend], key: str) -> Backend:
        fewest = min(b.inflight for b in backends)
        candidates = [b for b in backends if b.inflight == fewest]
        return self._rng.choice(candidates)  # random tie-break → even counts too


class PowerOfTwoChoices(LoadBalancer):
    """Sample two backends at random, route to the less loaded. O(1) state, yet
    provably close to least-connections (Mitzenmacher's 'power of two')."""

    name = "power-of-two"

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def choose(self, backends: list[Backend], key: str) -> Backend:
        a, b = self._rng.sample(backends, 2)
        return a if a.inflight <= b.inflight else b


class ConsistentHash(LoadBalancer):
    """Sticky routing: a key always lands on the same backend (session affinity,
    cache locality) — until membership changes. Virtual nodes even out the ring."""

    name = "consistent-hash"

    def __init__(self, backends: list[Backend], vnodes: int = 100) -> None:
        self._ring: list[tuple[int, Backend]] = []
        for b in backends:
            for v in range(vnodes):
                self._ring.append((self._hash(f"{b.name}#{v}"), b))
        self._ring.sort(key=lambda pair: pair[0])

    @staticmethod
    def _hash(key: str) -> int:
        return int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)

    def choose(self, backends: list[Backend], key: str) -> Backend:
        h = self._hash(key)
        lo, hi = 0, len(self._ring)
        while lo < hi:  # bisect on the sorted ring positions
            mid = (lo + hi) // 2
            if self._ring[mid][0] <= h:
                lo = mid + 1
            else:
                hi = mid
        return self._ring[lo % len(self._ring)][1]

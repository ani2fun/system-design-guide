"""ConsistentHashRing — the ring that decides which node owns a key.

Each physical node is placed at `vnodes` positions on a hash ring (virtual
nodes, so load spreads evenly). A key belongs to the first node clockwise from
its hash. Adding or removing a node reassigns only the keys between the changed
node and its neighbour — about 1/N of them — not the whole keyspace.
"""

from __future__ import annotations

import bisect
import hashlib


class ConsistentHashRing:
    def __init__(self, vnodes: int = 150) -> None:
        self._vnodes = vnodes
        self._ring: dict[int, str] = {}   # position → node
        self._positions: list[int] = []   # sorted positions
        self._nodes: set[str] = set()

    @staticmethod
    def _hash(key: str) -> int:
        return int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)

    def add_node(self, node: str) -> None:
        self._nodes.add(node)
        for v in range(self._vnodes):
            self._ring[self._hash(f"{node}#{v}")] = node
        self._positions = sorted(self._ring)

    def remove_node(self, node: str) -> None:
        self._nodes.discard(node)
        for v in range(self._vnodes):
            self._ring.pop(self._hash(f"{node}#{v}"), None)
        self._positions = sorted(self._ring)

    def node_for(self, key: str) -> str:
        if not self._positions:
            raise LookupError("ring is empty")
        idx = bisect.bisect_right(self._positions, self._hash(key)) % len(self._positions)
        return self._ring[self._positions[idx]]

    @property
    def nodes(self) -> set[str]:
        return set(self._nodes)

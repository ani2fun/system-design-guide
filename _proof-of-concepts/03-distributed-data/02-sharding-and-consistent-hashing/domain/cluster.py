"""SimulatedCluster — the nodes, mimicked as in-process key/value stores.

Each 'node' is a separate dict, standing in for a separate machine's storage.
`put`/`get` route through the ring; adding or removing a node rebalances by
moving only the keys whose owner changed — the whole point of consistent hashing.
The routing and rebalancing are exactly what a real distributed store does; only
the 'machines' are dicts in one process.
"""

from __future__ import annotations

from domain.ring import ConsistentHashRing


class SimulatedCluster:
    def __init__(self, ring: ConsistentHashRing) -> None:
        self._ring = ring
        self._stores: dict[str, dict[str, str]] = {node: {} for node in ring.nodes}

    def add_node(self, node: str) -> int:
        self._ring.add_node(node)
        self._stores.setdefault(node, {})
        return self._rebalance()

    def remove_node(self, node: str) -> int:
        # Removing a node only reassigns the keys it owned — every other node's
        # arc is untouched — so the moved count is exactly the orphaned set.
        self._ring.remove_node(node)
        orphaned = self._stores.pop(node, {})
        for key, value in orphaned.items():
            self._stores[self._ring.node_for(key)][key] = value
        return len(orphaned)

    def put(self, key: str, value: str) -> None:
        self._stores[self._ring.node_for(key)][key] = value

    def get(self, key: str) -> str | None:
        return self._stores[self._ring.node_for(key)].get(key)

    def distribution(self) -> dict[str, int]:
        return {node: len(store) for node, store in self._stores.items()}

    def _rebalance(self) -> int:
        """Re-place every key on its current owner; return how many actually moved."""
        placed = [(k, v, owner) for owner, store in self._stores.items() for k, v in store.items()]
        for store in self._stores.values():
            store.clear()
        moved = 0
        for key, value, previous_owner in placed:
            owner = self._ring.node_for(key)
            self._stores[owner][key] = value
            if owner != previous_owner:
                moved += 1
        return moved

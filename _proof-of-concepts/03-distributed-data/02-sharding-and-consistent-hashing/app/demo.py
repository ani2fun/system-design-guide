"""Demo — measure the two properties that make consistent hashing worth it:
minimal key movement on membership change, and even load thanks to virtual nodes.

Run: `./run demo`
"""

from __future__ import annotations

from domain.cluster import SimulatedCluster
from domain.ring import ConsistentHashRing

KEYS = [f"user:{i}" for i in range(100_000)]


def _spread(dist: dict[str, int]) -> str:
    lo, hi = min(dist.values()), max(dist.values())
    return f"min={lo:>6}  max={hi:>6}  spread={hi / lo:.2f}x"


def demo_minimal_movement() -> None:
    print("== Minimal movement: naive hash %N vs the ring ==")
    nodes = ["A", "B", "C", "D"]

    # Naive `hash(key) % N`: growing 4 -> 5 nodes remaps almost everything.
    before = {k: hash(k) % 4 for k in KEYS}
    after = {k: hash(k) % 5 for k in KEYS}
    naive_moved = sum(before[k] != after[k] for k in KEYS)
    print(f"  naive  %4 -> %5 : {naive_moved:>6} / {len(KEYS)} keys moved "
          f"({naive_moved / len(KEYS):.0%})")

    # The ring: adding a 5th node moves only ~1/5 of the keys.
    ring = ConsistentHashRing(vnodes=200)
    for n in nodes:
        ring.add_node(n)
    cluster = SimulatedCluster(ring)
    for k in KEYS:
        cluster.put(k, "1")
    moved = cluster.add_node("E")
    print(f"  ring  4 -> 5   : {moved:>6} / {len(KEYS)} keys moved "
          f"({moved / len(KEYS):.0%})  ideal ~1/5 = 20%")
    moved = cluster.remove_node("E")
    print(f"  ring  5 -> 4   : {moved:>6} / {len(KEYS)} keys moved "
          f"(only the removed node's keys)")


def demo_virtual_nodes() -> None:
    print("\n== Virtual nodes even out load (5 nodes, 100k keys) ==")
    for vnodes in (1, 10, 200):
        ring = ConsistentHashRing(vnodes=vnodes)
        cluster = SimulatedCluster(ring)
        for n in ["A", "B", "C", "D", "E"]:
            cluster.add_node(n)
        for k in KEYS:
            cluster.put(k, "1")
        print(f"  vnodes={vnodes:<4} {_spread(cluster.distribution())}")


if __name__ == "__main__":
    demo_minimal_movement()
    demo_virtual_nodes()

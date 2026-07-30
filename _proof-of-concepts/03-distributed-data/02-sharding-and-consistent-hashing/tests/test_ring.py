from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.cluster import SimulatedCluster  # noqa: E402
from domain.ring import ConsistentHashRing  # noqa: E402

KEYS = [f"k:{i}" for i in range(20_000)]


def _fresh_cluster(nodes: list[str], vnodes: int = 200) -> SimulatedCluster:
    ring = ConsistentHashRing(vnodes=vnodes)
    for n in nodes:
        ring.add_node(n)
    cluster = SimulatedCluster(ring)
    for k in KEYS:
        cluster.put(k, k.upper())
    return cluster


def test_routing_is_deterministic() -> None:
    ring = ConsistentHashRing(vnodes=50)
    for n in ["A", "B", "C"]:
        ring.add_node(n)
    assert all(ring.node_for("x") == ring.node_for("x") for _ in range(5))


def test_empty_ring_raises() -> None:
    ring = ConsistentHashRing()
    try:
        ring.node_for("x")
    except LookupError:
        return
    raise AssertionError("expected LookupError on empty ring")


def test_adding_node_moves_about_one_over_n() -> None:
    cluster = _fresh_cluster(["A", "B", "C", "D"])
    moved = cluster.add_node("E")
    fraction = moved / len(KEYS)
    # Ideal is 1/5 = 0.20; allow a generous band for hash variance.
    assert 0.10 < fraction < 0.30, fraction


def test_data_survives_rebalance() -> None:
    cluster = _fresh_cluster(["A", "B", "C"])
    cluster.add_node("D")
    cluster.remove_node("A")
    assert all(cluster.get(k) == k.upper() for k in KEYS)


def test_removed_node_keys_are_rehomed() -> None:
    cluster = _fresh_cluster(["A", "B", "C", "D"])
    cluster.remove_node("C")
    assert "C" not in cluster.distribution()
    assert sum(cluster.distribution().values()) == len(KEYS)


def test_virtual_nodes_improve_balance() -> None:
    coarse = _fresh_cluster(["A", "B", "C", "D", "E"], vnodes=1).distribution()
    fine = _fresh_cluster(["A", "B", "C", "D", "E"], vnodes=300).distribution()
    coarse_spread = max(coarse.values()) / min(coarse.values())
    fine_spread = max(fine.values()) / min(fine.values())
    assert fine_spread < coarse_spread
    assert fine_spread < 1.3


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"PASS  {len(fns)} consistent-hash tests")

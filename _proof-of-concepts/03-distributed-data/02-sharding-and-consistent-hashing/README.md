# POC: Consistent Hashing

A runnable companion to **Sharding & consistent hashing**
(`03-distributed-data/02-sharding-and-consistent-hashing`). It shows the two
properties that make the ring worth its complexity:

1. **Minimal movement.** Growing from N to N+1 nodes relocates only ~1/(N+1) of
   the keys — not the whole keyspace, the way naive `hash(key) % N` does.
2. **Even load.** Virtual nodes (many ring positions per physical node) flatten
   the per-node imbalance that a handful of positions would leave.

| Piece | File | Role |
| --- | --- | --- |
| `ConsistentHashRing` | [`domain/ring.py`](domain/ring.py) | positions nodes on a SHA-256 ring; `node_for(key)` walks clockwise |
| `SimulatedCluster` | [`domain/cluster.py`](domain/cluster.py) | one dict per node ("machine"); routes puts/gets, counts keys moved on rebalance |

## Run it

```bash
./run            # the demo: movement + balance numbers
./run test       # mypy --strict + unit tests + demo
./run check      # mypy only
```

Uses [`uv`](https://docs.astral.sh/uv/); no Docker, no ports, standard library only.

## What the demo proves

```
== Minimal movement: naive hash %N vs the ring ==
  naive  %4 -> %5 : ~80% of keys moved
  ring  4 -> 5    : ~20% of keys moved   (ideal 1/5)
  ring  5 -> 4    : only the removed node's keys moved

== Virtual nodes even out load ==
  vnodes=1    spread ~2x between the busiest and quietest node
  vnodes=200  spread ~1.05x — effectively balanced
```

## What is simulated vs. real

Real consistent hashing (Dynamo, Cassandra, a Redis-cluster client, a CDN) runs
across **many machines**, each holding a shard of the data. This POC **mimics
the machines in one process**: each node is a separate `dict` inside
`SimulatedCluster`, standing in for a separate machine's local store. Moving a
key from one dict to another stands in for streaming a key range between two
servers over the network.

What is **identical to production**, not simulated: the ring itself — the hash
function, the virtual-node placement, the clockwise `node_for` lookup, and the
rebalancing math. The "~1/N keys move" and "virtual nodes even out load"
results you see here are the exact reason real systems choose this scheme; only
the transport (a dict write instead of a network transfer) is faked. There is no
replication factor, no failure detection, and no cross-node coordination here —
those live in the lesson, not this POC.

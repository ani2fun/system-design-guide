---
title: Counter state
kind: Cache
technology: Redis
---

## ⚡ Counter state

**Counter state** is the mutable heart of the design — per-key windows and buckets, written on *every allowed request* at 1M checks/second. It exists because the limit is a **global statement**: a user capped at 100/minute across five gateway nodes needs one counter all five consult, or each node sees only its slice and the effective limit becomes 100 × the node count, modulated by load-balancer luck. Local counters were never enough; shared state is the whole point.

**Responsibilities**

- Hold, per key, exactly what the algorithm must remember — for the chosen token bucket, two numbers: current tokens and last-refill timestamp.
- Execute the Lua script (`EVALSHA`) as **one atomic unit**, single-threaded, so concurrent check-and-increments serialize instead of losing updates.
- Self-clean: an `EXPIRE` of ~1 hour, refreshed on each check, so idle keys evaporate instead of leaking memory forever.
- Scale by **sharding on the key** — Redis Cluster's 16,384 hash slots — with the non-negotiable rule that all of one key's traffic lands on one shard, or the key's state splits and the per-node bug is rebuilt inside the data layer. One instance handles ~100k–200k ops/second; ~10 shards meets 1M checks/second. Capacity is not the issue: 10M active buckets fit in roughly 1.5 GB.

**Where it breaks.** Hot keys — one aggressive client concentrates on one shard no matter how many exist — and failover: replication is asynchronous, so a promoted replica can forget recently spent tokens. Race-free is not the same as exact under replication; seconds of over-admission is a trade this design makes knowingly.

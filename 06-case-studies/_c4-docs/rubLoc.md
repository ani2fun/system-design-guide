---
title: Location service
kind: Service
technology: Python · FastAPI
---

## ⚙️ Location service

The **Location service** exists for one reason: the ping firehose must not touch anything else. Roughly 10 million drivers pinging every 5 seconds is about **2 million writes per second** — two orders of magnitude beyond what a durable relational store sustains, and the naive design dies here first. Worse, the writes are unlike everything else in the system: each ping *overwrites* the last, nobody ever queries where a driver was 40 seconds ago, and the value expires in seconds. Paying durable-storage prices — WAL, replication, B-tree maintenance — for that data is the wrong store for the data's lifetime. So this container is the firehose's **only** consumer: a thin, stateless write path that nothing else shares.

**Responsibilities**

- Accept every driver ping from the gateway and turn it into a `GEOADD` plus a freshness TTL on the geo index — write-through, no batching, so there is no staleness window on the write path.
- Do nothing else. No reads, no ride logic, no durable writes; its isolation *is* the design decision.

**Where it grows.** Horizontally without ceremony — it holds no state, so instances scale with ping volume; the real lever is upstream, where adaptive ping intervals (stationary drivers ping rarely, fast movers often) cut the write rate at the source.

**Where it breaks.** If it backs up, the geo index goes stale and matching quietly degrades — offers go to drivers who have moved on. The TTL bounds the damage: positions that stop refreshing evaporate rather than lie.

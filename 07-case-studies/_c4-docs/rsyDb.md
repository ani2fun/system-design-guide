---
title: Submissions store
kind: Relational database
technology: PostgreSQL
---

## 🗄️ Submissions store

The only entity in the system that grows: submissions (user, problem, source, verdict, per-case
results) plus the allowlist grants. Everything else is either derived from git (content) or
ephemeral (runs).

**Why one Postgres is the whole answer**

The napkin math at 1M MAU: <1 submission/s, ~2 KB/row → ~400 MB/day worst case. Time-partitioned
tables hold years of that on a single primary; older partitions archive to object storage. The
sharding conversation has a written trigger — *"write volume breaks the napkin math"* — and until it
fires, distributed-database complexity is deliberately not purchased.

**The judging lifecycle it anchors**

A submission row advances `pending → completed` as the judge runs the hidden suite. If the judge
dies mid-suite, the row is still `pending`; a reaper re-enqueues stale rows and judging re-runs
from the top — safe because verdict computation is **idempotent** (same source, same suite, same
verdict), so at-least-once execution converges without exactly-once machinery.

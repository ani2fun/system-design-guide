---
title: ID range allocator
kind: Relational database
technology: PostgreSQL (sequence table)
---

## 🗄️ ID range allocator

The **ID range allocator** is one integer with strong opinions: a single fetch-and-add row that hands out disjoint counter ranges — `[from, to)` — to API nodes. It exists because uniqueness by construction beats collision checking (hashing to 6 base62 characters yields ~8.8M expected collisions at 1B codes), but a *per-write* global counter would put a single round trip, throughput ceiling, and point of failure on every insert. Batching is the pressure release: lease ~1,000 ids at a time and the allocator is contacted once per thousand writes.

**Responsibilities**

- Atomically advance the counter by the batch size and return the leased range — disjoint ranges are what make concurrent API nodes collision-free with zero coordination between them.
- Persist the new high-water mark durably **before** the range is released to the caller — so recovery over-skips rather than repeats.

Two consequences are deliberate. Crashed API nodes abandon the unissued remainder of their range, so the code sequence has gaps — harmless, because the requirement is uniqueness, not density (gaps are even useful: they tell on your crash rate). And global creation order is quietly gone once several nodes hold outstanding ranges — which costs nothing, since codes are opaque names nobody compares.

**Where it breaks.** Failover. If the allocator's state replicates asynchronously and it fails over, the replica may have missed the latest advance — and a stale counter re-issues a range, meaning **duplicate codes**, the one unforgivable event in this system. The fix is not *"add Raft"* as a slogan; it is one sentence: this tiny state must survive failover without losing acknowledged increments. Alarm on issued-range history — a re-issue is a catastrophe in progress.

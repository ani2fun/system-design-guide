---
title: RangeLease
kind: Code
technology: Python
---

## 🧩 RangeLease

**RangeLease** is the class that removes the global counter from the write path. Instead of one allocator round trip per link, it leases a *block* of ids — `[from, to)`, via a single batched fetch-and-add on the **ID range allocator** — and serves `next_id()` from local memory until the block runs dry.

**Responsibilities**

- Lease a fresh disjoint range from the allocator when none is held, and refresh **before exhaustion** so a lease round trip never lands in a request's latency.
- Serve `next_id()` locally — an increment, not a network call — making writes collision-free with zero coordination between API nodes.
- On restart, hold nothing: a new node simply leases a new range.

The design's two deliberate consequences live here. A node that crashes mid-range abandons the unissued remainder — the sequence has gaps, which are harmless because the requirement is uniqueness, not density. And global creation order is gone once several nodes hold ranges — which costs nothing, since codes are opaque names nobody compares.

**The invariant it protects:** a crash produces **gaps, never duplicates**. RangeLease never persists its cursor and never resumes an old range; because the allocator advanced its high-water mark *before* releasing the lease, recovery over-skips rather than repeats, and no id is ever served twice.

**Where it breaks.** Only through its supplier: an allocator that fails over onto stale state can re-issue a range, and duplicate ids become duplicate codes. The class itself cannot detect that — the defense lives in the allocator's durability. Implemented in the forthcoming POC at `06-case-studies/examples/url-shortener/app/range_lease.py`.

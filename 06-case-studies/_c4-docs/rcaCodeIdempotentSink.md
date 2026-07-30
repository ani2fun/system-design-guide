---
title: IdempotentSink
kind: Code
technology: Python (OLAP upsert writer)
---

## 🧩 IdempotentSink

**IdempotentSink** is where the honest asterisk on *"exactly-once"* gets handled. Checkpointing restores the aggregator's counters perfectly — state and input offsets snapshot together, so recovery neither skips nor double-applies a click to *state*. What it cannot do is un-write the rows flushed to the OLAP store between the last checkpoint and the crash: exactly-once is effectively-once **within the framework's boundary**, and a restarted task performs its external side effects *again*. The two escapes are atomic commit kept inside the framework, or idempotent writes — and this design's output shape makes idempotence the natural fit: aggregates are keyed rows, so writing the same row twice can be made to converge instead of double.

**Responsibilities**

- `flush(window_counts)`: write every emitted window as an **UPSERT keyed by (ad, window)** — never an INSERT — so a replayed flush overwrites the same row with the same value, and recovery never double-counts.
- Serve all three writers of the same contract: final window closes, late-click corrections, and batch reconciliation's fixes — one row identity, any number of safe rewrites.
- Honor idempotence's fine print: replays must be deterministic and in-order, and failover needs fencing so a presumed-dead task can't keep writing stale values over fresh ones.

**The invariant it protects:** *replay-safe upserts keyed by (ad, window)* — effectively-once state inside, idempotent effects outside.

**Where it breaks.** Idempotence dedups identical aggregate *writes*, not duplicate *events* — a double-counted click is already inside the number by the time it reaches this class, which is why the deduper upstream exists. Mirrored by the forthcoming POC at `06-case-studies/examples/ad-click-aggregator/app/idempotent_sink.py`.

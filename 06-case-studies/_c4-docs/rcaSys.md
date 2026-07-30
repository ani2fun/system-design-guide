---
title: Ad-Click Aggregator
kind: System
technology: Log + stream + OLAP + batch reconciliation
---

## 🏢 Ad-Click Aggregator

The **Ad-Click Aggregator** does one thing — count clicks — at 10k events/second, across machines that crash, retry, and redeliver, correctly enough that advertisers are billed on the result. That last clause is the whole design: an overcounted click is an overcharged advertiser, an undercounted one is revenue silently dropped, and a wrong count is *perpetual* until something detects and repairs it. So the architecture is two paths over one immutable log: a **stream** path (log → event-time windows → OLAP) that is fast and almost always right, and a **batch** path (raw archive → periodic recompute) that makes it provably right. Dashboards run on the stream; invoices trust the reconciliation.

**Responsibilities**

- Ingest every click exactly once *in effect*: verify the signed impression ID, dedup at the door, append to a partitioned log — salted for viral ads so one hot key can't melt a shard.
- Aggregate by **event time**, not processing time, with a watermark deciding when a window is complete enough to emit — so a consumer restart never bills a phantom click spike.
- Serve pre-aggregated `(ad, minute)` rows with sub-second latency, and keep them honest with idempotent upserts and batch corrections.

**Where it breaks.** Every guarantee inside the pipeline has a boundary: *"exactly-once"* is effectively-once *state* within the framework, and side effects crossing out of it replay on failure. The system survives that not by trusting any single mechanism but by layering three — end-to-end impression IDs, checkpointed state, idempotent sinks — plus the reconciliation audit for whatever slips through.

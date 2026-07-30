---
title: Aggregates store
kind: Data warehouse
technology: OLAP store
---

## 📊 Aggregates store

The **Aggregates store** holds the rows the whole system exists to compute: `(ad_id, minute_bucket) → click_count`, pre-aggregated so the advertiser's dashboard reads answers instead of computing them. It embodies the design's corrected instinct — move work from the read path to the write path. The naive alternative (GROUP BY over raw clicks at query time) re-scans millions of rows per dashboard refresh; here the aggregation happened once, upstream, and a week-long query touches ~10,080 pre-built rows. Sub-second latency is a property of the *shape* of the data, not of heroic query optimization.

**Responsibilities**

- Serve the Metrics API's range reads at minute granularity, with day/week roll-up tables shrinking long-range queries further.
- Accept writes as **upserts keyed by (ad, window)**, never blind inserts — the property that makes replayed flushes, late-click corrections, and batch reconciliation all converge on the same row instead of doubling it. Three writers, one idempotent contract.
- Hold provisional values for open windows (early flushes) that later flushes overwrite with finals.

**Where it breaks.** Two edges. Salted hot ads land as N sub-rows whose totals must be merged at query time or by a second-stage aggregation — the read-side tax salting always charges. And batch corrections must arrive through controlled ingestion, not raw per-row UPDATE storms: batch jobs writing straight into a live serving store throttle the job and degrade query latency — the reason real-time OLAP engines ingest from streams by design.

---
title: Click log
kind: Event stream
technology: Kafka
---

## 🌊 Click log

The **Click log** is the component nothing is allowed to shortcut: an append-only, partitioned sequence of immutable click events, totally ordered within each shard. It buffers (a click spike or a slow consumer widens the lag instead of dropping data — the peak is ~8× the average, and the log is what lets consumers be sized nearer the average), it retains (~7 days: consumption is non-destructive, so a crashed job rewinds its offset and re-reads), and it *is* the recent system of record — every downstream artifact, from Flink's counters to the OLAP rows to the S3 archive, is a derived view recomputable from it. Count-affecting disputes end at the log, or they don't end.

**Responsibilities**

- Shard by **AdId**, so each ad's events land in one shard in total order and each stream task aggregates its ads with purely local state — no cross-shard coordination on the hot path.
- **Salt hot keys**: a viral ad's clicks all hash to one shard, whose throughput cap becomes the ad's ceiling. For hot ads only, the key becomes `AdId:0…N` across N shards — splitting the write load at the cost of N partial counts that must be merged downstream. Salt the few, not the many.
- Feed two consumers: the stream aggregator (fast path) and the raw archive (truth path).

**Where it breaks.** Retention is the outage budget: a consumer that falls behind by more than the retention window starts missing events *permanently*. *"7 days"* really means *"we can survive a long weekend of pipeline failure and still recompute."*

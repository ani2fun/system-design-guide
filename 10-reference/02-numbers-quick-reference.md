---
title: "Numbers Quick Reference"
summary: "The one-page latency, capacity, and availability figures to glance at before an interview — every number attributed."
essential: false
---

# 🔢 Numbers Quick Reference

This is the lookup sheet: the latency ladder, capacity ceilings, and availability math you want in your head before a design interview. It teaches nothing — the *method* (how to turn these into an estimate) lives in [Estimation & the Numbers](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers), and the intuition behind latency and percentiles lives in [Latency, Throughput & Percentiles](/synapse/system-design-from-first-principles/foundations/latency-throughput-percentiles). Here we just tabulate.

Every cell names its source: **`DDIA2 ch.N p.X`** (Designing Data-Intensive Applications, 2nd ed.), **`industry practice`** (widely-known operational figures observed across production systems, not from a single cited source), or **`RoT`** (rule of thumb — widely-known and arithmetic figures, not from a cited source).

<div style="border-left:4px solid #195045;background:rgba(25,80,69,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

💡 **Read the ratios, not the digits.** These are orders of magnitude, not precise measurements — hardware, cloud pricing, and instance ceilings drift year to year. The point is that RAM is ~100× faster than SSD, cross-region is ~100× a same-DC round trip, and a fan-out of 200 turns 5,800 writes/s into a million. If you remember the *shape*, you can rebuild the digits.

</div>

## 🪜 The latency ladder

The canonical *"how long does it take"* ordering. The nanosecond memory figures are the widely-taught *Latency Numbers Every Programmer Should Know* set (order-of-magnitude, hardware-dependent); the round-trip and in-practice figures come from the sources.

| quantity | value | context | source |
| --- | --- | --- | --- |
| L1 cache reference | ~1 ns | on-die, per access | RoT |
| L2 cache reference | ~4 ns | on-die | RoT |
| Main memory (RAM) reference | ~100 ns | ~100× slower than L1 | RoT |
| SSD random read (raw device) | ~16–150 µs | flash page read | RoT |
| Disk (HDD) seek | ~10 ms | mechanical head move | RoT |
| Cache read (Redis/Memcached, in practice) | < 1 ms | includes a network hop on the same DC | industry practice |
| DB read, cached page | ~1–5 ms | served from buffer pool | industry practice |
| DB read, from disk | ~5–30 ms | includes storage + engine overhead | industry practice |
| DB write commit | ~5–15 ms | durable (WAL flush) | industry practice |
| Same-DC / intra-region round trip | ~1–2 ms (< 1 ms nearby) | LAN hop | industry practice |
| Cross-region round trip | ~50–150 ms | e.g. US ↔ EU | industry practice |
| NY ↔ London, theoretical minimum | ~56 ms | speed of light in fiber (~⅔ c) over ~5,600 km | RoT |
| Cross-continent round trip (typical) | > 80 ms | vs < 1 ms for a nearby host | industry practice |

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **Trap.** Candidates routinely *over-estimate* single-machine latency — a plain SSD-backed row lookup is often cited at "~10 ms" and cached against needlessly, when the DB itself does 20k+ simple writes/s. Don't add a cache to dodge a millisecond you never had.

</div>

---

## 🚀 Throughput & capacity per node

Rough single-box ceilings, and the load level that signals it's time to shard. Hardware ceilings drift year to year — treat the specific numbers as 2025-era industry figures, the *shape* as durable.

| component | throughput / capacity | shard/scale trigger | source |
| --- | --- | --- | --- |
| Cache (Redis/Memcached) instance | 100k+ ops/sec; up to ~1 TB memory | ~1 TB dataset or 100k+ ops/sec | industry practice |
| DB single node — reads | up to ~50k read TPS | — | industry practice |
| DB single node — writes | ~10–20k write TPS | > 10k write TPS | industry practice |
| DB single node — storage | ~64–128 TiB | ~50 TiB | industry practice |
| DB single node — connections | ~5k–20k concurrent | — | industry practice |
| Postgres — simple writes | 20k+ writes/sec | (don't queue below this) | industry practice |
| Application server | 100k+ concurrent connections; 8–64 cores; 64–512 GB RAM | — | industry practice |
| Message broker (Kafka-class) | up to ~1M msgs/sec/broker; 1–5 ms end-to-end; up to ~50 TB/broker | ~800k msgs/sec or ~200k partitions/cluster | industry practice |
| Amazon Aurora cluster-volume ceiling | 128 TiB; **256 TiB** on current engine versions | the classic "now you must shard" line | [web: AWS Aurora quotas] |

---

## 💾 Storage & data sizes

Per-value sizes are general-knowledge (`RoT`); the storage-engine figures are cited to DDIA.

| quantity | value | context | source |
| --- | --- | --- | --- |
| ASCII / single-byte char | 1 byte | UTF-8 is 1–4 bytes/char | RoT |
| Integer (32-bit) | 4 bytes | 8 bytes for a 64-bit long/bigint | RoT |
| UUID | 16 bytes (128-bit) | 36 chars as a hyphenated string | RoT |
| Unix timestamp | 8 bytes | ms/µs since 1970 epoch | RoT |
| Typical "row-ish" record | ~1 KB | common back-of-envelope unit (e.g. a post, a profile) | RoT |
| B-tree page (traditional) | 4 KiB | PostgreSQL uses 8 KiB, MySQL 16 KiB | DDIA2 ch.4 p.125 |
| B-tree branching factor | several hundred (~500) | children per page | DDIA2 ch.4 pp.126–127 |
| 4-level B-tree capacity | up to ~250 TB | 4 KiB pages, branching factor 500 | DDIA2 ch.4 p.127 |
| B-tree depth for most databases | 3–4 levels | O(log n), stays balanced | DDIA2 ch.4 p.127 |
| Flash page (read/write unit) | ~4 KiB | but erase happens per ~512 KiB block | DDIA2 ch.4 p.130 |
| LSM memtable flush threshold | a few MB | when it flushes to an SSTable | DDIA2 ch.4 p.120 |

**Powers of 2 vs 10** (the conversion you do in your head — arithmetic, `RoT`):

| power of 2 | ≈ power of 10 | name | bytes shorthand |
| --- | --- | --- | --- |
| 2¹⁰ = 1,024 | 10³ | thousand | KB |
| 2²⁰ ≈ 1.05 M | 10⁶ | million | MB |
| 2³⁰ ≈ 1.07 B | 10⁹ | billion | GB |
| 2⁴⁰ ≈ 1.10 T | 10¹² | trillion | TB |
| 2⁵⁰ | 10¹⁵ | quadrillion | PB |

See [Specialized Stores](/synapse/system-design-from-first-principles/building-blocks/specialized-stores) for the per-store sizing that builds on these.

---

## 🗓️ Time & the calendar

The conversions that turn *"per day"* into *"per second."* Arithmetic unless cited.

| quantity | value | context | source |
| --- | --- | --- | --- |
| Seconds per day | ~86,400 | 24 × 3,600 (a day is *usually* but not exactly this — leap seconds) | DDIA2 ch.9 p.362 · RoT |
| Seconds per month (30 d) | ~2.5 million | 2,592,000 | RoT |
| Seconds per year | ~31.5 million | ≈ π × 10⁷ is the classic mnemonic | RoT |
| 1 million events/day → per second | ~12 /s | 1,000,000 ÷ 86,400 | RoT |
| 500 million posts/day → per second | 5,800 /s average | DDIA social-network case study | DDIA2 ch.2 p.34 |
| Peak-to-average spike (same workload) | up to 150,000 /s | vs 5,800 /s average — plan for the peak | DDIA2 ch.2 p.34 |
| Fan-out factor (avg followers) | 200 | turns 5,800 posts/s into ~1M timeline writes/s | DDIA2 ch.2 p.36 |
| Timeline writes/second (fan-out on write) | just over 1 million | 5,800 × 200 | DDIA2 ch.2 p.36 |
| Naive per-read fan-out (polling) | 400 million lookups/s | 2M timeline queries/s × 200 follows | DDIA2 ch.2 p.35 |

The lesson of the last three rows: the same workload is ~1M writes/s if you fan out on write, or 400M lookups/s if you fan out on read — see [Fan-out: Push vs Pull](/synapse/system-design-from-first-principles/patterns/fan-out-push-vs-pull).

---

## ⏱️ Clocks, faults & the network

The distributed-systems reality figures — all from DDIA ch. 9. These are the numbers that justify timeouts, fencing tokens, and never trusting a wall-clock for ordering.

| quantity | value | context | source |
| --- | --- | --- | --- |
| Network faults (medium datacenter) | ~12 /month | half disconnect one machine, half a whole rack | DDIA2 ch.9 p.350 |
| Cross-region RTT, high percentile | up to several minutes | assume messages are arbitrarily delayable | DDIA2 ch.9 p.350 |
| Intra-DC packet delay (topology reconfig) | more than a minute | during a switch software upgrade | DDIA2 ch.9 p.350 |
| Timeout bound (hypothetical) | 2d + r | max packet delay d + max node handling r; doesn't hold on real async networks | DDIA2 ch.9 pp.352–353 |
| Quartz clock drift (Google assumption) | up to 200 ppm | ≈ 6 ms if resynced every 30 s; ≈ 17 s/day if resynced daily | DDIA2 ch.9 p.360 |
| NTP sync error over the internet | ~35 ms minimum, spikes to ~1 s | limited by network round-trip time | DDIA2 ch.9 p.361 |
| NTP slew limit | up to 0.05% clock-rate adjustment | can speed/slow but not jump a monotonic clock | DDIA2 ch.9 p.360 |
| Best internet clock accuracy | tens of ms (> 100 ms under congestion) | why microsecond timestamp digits are meaningless | DDIA2 ch.9 pp.364–365 |
| Spanner TrueTime clock sync | within ~7 ms | per-DC GPS/atomic clock; commit-wait ≈ the interval width | DDIA2 ch.9 p.366 |
| MiFID II clock-sync requirement | within 100 µs of UTC | high-frequency trading regulation | DDIA2 ch.9 p.361 |
| Modern GC pause (well-tuned) | a few ms | historically stop-the-world GC ran to several minutes | DDIA2 ch.9 pp.367, 370 |
| VM pause (another VM using the core) | tens of ms | shows up as a forward clock jump on resume | DDIA2 ch.9 pp.353, 361 |
| Majority-quorum fault tolerance | 3 nodes → 1 fault; 5 → 2 | absolute majority (> half) | DDIA2 ch.9 pp.372–373 |
| Byzantine fault tolerance | supermajority > ⅔ (4 nodes → 1) | most BFT algorithms | DDIA2 ch.9 p.379 |

See [Faults, Clocks & Time](/synapse/system-design-from-first-principles/distributed-data/faults-clocks-and-time) for why each of these matters.

---

## 🟢 Availability

The *"nines"* translated to allowed downtime. Standard arithmetic (`RoT`) — memorize the middle three rows; they anchor almost every SLA conversation.

| availability | downtime / year | downtime / month | typical framing |
| --- | --- | --- | --- |
| 99% ("two nines") | ~3.65 days | ~7.3 hours | a hobby project |
| 99.9% ("three nines") | ~8.77 hours | ~43.8 min | a common SLA floor |
| 99.99% ("four nines") | ~52.6 min | ~4.4 min | a serious production target |
| 99.999% ("five nines") | ~5.26 min | ~26 s | telco / core infra |
| 99.9999% ("six nines") | ~31.5 s | ~2.6 s | rarely real end-to-end |

All rows: `RoT` (downtime = (1 − availability) × period). Remember that availability *multiplies* across a serial dependency chain: five services each at 99.9% give ~99.5% combined, not 99.9%.

---

## 📊 Percentiles & SLOs

What the tail numbers mean and why they dominate user experience. All from DDIA ch. 2.

| quantity | value / meaning | context | source |
| --- | --- | --- | --- |
| Median (p50) | half of requests faster, half slower | the "typical" wait — never quote the mean | DDIA2 ch.2 p.40 |
| p95 example | 95/100 requests finish under this | e.g. a p95 of 1.5 s | DDIA2 ch.2 p.40 |
| p99 / p999 | slowest 1 in 100 / 1 in 1,000 | the "tail latency" that hits your best customers | DDIA2 ch.2 p.40 |
| Amazon internal target | 99.9th percentile | slowest requests often = most valuable users (most data) | DDIA2 ch.2 pp.40–41 |
| Amazon's diminishing-returns line | 99.99th percentile | deemed too costly to optimize for the benefit | DDIA2 ch.2 p.41 |
| Example SLO | median < 200 ms; p99 < 1 s; ≥ 99.9% non-error | a representative service-level objective | DDIA2 ch.2 pp.41–42 |
| Tail-latency amplification | more backend calls ⇒ higher chance ≥ 1 is slow | one slow parallel call slows the whole request | DDIA2 ch.2 p.41 |

<div style="border-left:4px solid #15448e;background:rgba(21,68,142,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

**Definition.** *Averaging percentiles is mathematically meaningless.* To aggregate response times across machines or time windows, add the **histograms** — never average the p99s. (DDIA2 ch.2 p.42.)

</div>

Related capacity figures live in [Capacity & Autoscaling](/synapse/system-design-from-first-principles/production-engineering/capacity-and-autoscaling).

## PoC — Proof of concepts

The primary sources for the numbers on this page — check them rather than trusting a memorised table:

- [Latency numbers, interactive](https://colin-scott.github.io/personal_website/research/interactive_latency.html)
  — the canonical constants, adjustable by year so you use current figures, not 2005's.
- [The original latency-numbers gist](https://gist.github.com/jboner/2841832) — the plain table these
  quick-reference numbers derive from.
- [System Design Primer — appendix](https://github.com/donnemartin/system-design-primer) —
  powers of two, availability-in-nines and the QPS/storage estimation examples to apply them.

## Sources

- **DDIA2 ch.2** — *Defining Nonfunctional Requirements*, pp. 34–46 (fan-out math, percentiles/SLOs, hardware failure rates).
- **DDIA2 ch.4** — *Storage and Retrieval*, pp. 120–130 (B-tree page sizes, branching factor, flash page/block, memtable threshold).
- **DDIA2 ch.9** — *The Trouble with Distributed Systems*, pp. 350–379 (clock drift, NTP, GC pauses, network faults, timeout bound, Spanner, quorum/BFT).
- **Industry-standard latency/throughput references** — widely-known latency ladder in-practice figures, per-node throughput/capacity ceilings, shard triggers, RTT figures, and named cloud-service ceilings. Hardware ceilings are 2025-era; treat specific numbers as approximate and refresh against current instance types.
- **[web: AWS Aurora quotas and constraints]** — the Aurora cluster-volume ceiling, verified 2026-08: 256 TiB on Aurora PostgreSQL 17.5+/16.9+/15.13+ and Aurora MySQL 3.10+, 128 TiB on all earlier versions. Note the unit is **TiB**, and the ceiling is per *cluster volume* — shared by all 15 replicas — not per instance.

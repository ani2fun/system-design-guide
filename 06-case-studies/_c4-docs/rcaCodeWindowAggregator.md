---
title: WindowAggregator
kind: Code
technology: Python (event-time windowing)
---

## 🧩 WindowAggregator

**WindowAggregator** answers the question that sounds trivial and isn't: *which minute does this click belong to?* A click has two timestamps — event time (when it happened) and processing time (when this operator handles it) — and bucketing by the wrong one turns a restart's backlog into a phantom traffic spike billed into the recovery minute, while the outage minutes look eerily quiet. So it buckets by **event time**, into tumbling one-minute windows: fixed length, every click in exactly one window, one counter incremented per click — small state, no event buffers. Event time is also what keeps *replay* meaningful: on reprocessing, *"now"* is wrong but the event stamps are still true.

**Responsibilities**

- `ingest(click)`: round the event timestamp down to its minute and increment that window's counter per ad — flushing provisional values while the window is open, so the current minute is live on dashboards.
- `on_watermark(ts) → list~WindowCount~`: when the watermark — the assertion that nothing earlier than *ts* is coming — passes a window's end, close it and emit its final counts.
- Route stragglers deliberately: a click arriving after its window closed forks to a **correction** (an upsert against the already-flushed row) rather than a silent drop — for billing, corrections beat quietly uncounted money.

**The invariant it protects:** *the watermark closes windows; late clicks fork to correction* — no window is final by wall clock, only by evidence.

**Where it breaks.** The watermark is a heuristic bound, not an oracle: set it tight and corrections multiply; set it loose and finality lags. Mirrored by the forthcoming POC at `06-case-studies/examples/ad-click-aggregator/app/window_aggregator.py`.

---
title: Click stream
kind: Event stream
technology: Redis Stream
---

## 🌊 Click stream

The **Click stream** is the design's async boundary: a queue that carries one small event per redirect into the analytics pipeline, so that counting clicks never adds a microsecond to serving them. It exists because the lesson chose `302` over `301` precisely to *keep* click data — and then must make that data free on the hot path.

**Responsibilities**

- Accept a click event from the **RedirectHandler**, **fire-and-forget** — the `302` is already on its way before the event lands; a redirect never waits on a click write.
- Buffer bursts (a viral link means hundreds of thousands of clicks per second on one code) as *lag* in the stream, not as latency on redirects.
- Feed downstream analytics consumers at their own pace.

The asymmetry is the design decision: redirects have a 100 ms budget and a four-nines target; click counts have neither. Splitting them means the analytics pipeline can fall behind, restart, or be rebuilt without the redirect path noticing.

**Where it breaks.** Fire-and-forget means exactly what it says: an API node that crashes between sending the `302` and emitting the event loses that click, and nobody reconciles it. That is a deliberate trade — approximate analytics for an untouched hot path — but say it out loud, because *"clicks"* quietly becoming *"billing"* would invalidate it. The metric to watch is consumer lag age, not stream depth: a stalled consumer with a shallow-looking stream is still an outage for analytics.

---
title: Fan-out queue
kind: Event stream
technology: Redis Stream
---

## 🌊 Fan-out queue

The **Fan-out queue** buffers post events between the API and the workers — it is the **async boundary** of the design, the line where *"handle it before returning 201"* ends and *"handle it within the freshness SLO"* begins.

**Responsibilities**

- Accept a small `{postId, authorId}` event from the **Feed API** the moment a post is stored; the author's `201` never waits for delivery.
- Hold events through spikes — posting peaks hit ~26× the average (150k posts/s vs 5,800/s), and the queue absorbs that burst as *lag* rather than as blocked writes or a melted timeline store.
- Deliver events to the **Fan-out workers** with **at-least-once** semantics: an event whose processing crashes is redelivered, never dropped.

Why a queue at all: the fan-out (~200 timeline writes per post, ~1M/s fleet-wide) is too much work for the request path, but it's *deferrable* work — the target is a post reaching followers within ~5 seconds, an SLO on this pipeline, not a request deadline.

**Where it breaks.** At-least-once means duplicates by design — safe only because the downstream insert is idempotent. Queue *depth* is a misleading health metric: one celebrity-sized job can starve everything behind it while depth looks fine, so the number to watch is the age of the oldest undelivered post. The queue converts overload into staleness — which is precisely the trade the 1-minute staleness NFR authorizes.

---
title: News Feed
kind: System
technology: Hybrid fan-out (push + read-time merge)
---

## 🏢 News Feed

The **News Feed** system answers one question fast — *"what did the people I follow post, newest first?"* — for 2 billion users. One piece of arithmetic rules every box inside it: computing the feed at read time costs **400M lookups/s** (2M polling queries × ~200 followed accounts), while precomputing it at write time costs **~1M timeline writes/s** (5,800 posts/s × ~200 followers). Push wins ~400×, so the system materializes every user's timeline in advance — *except* where fan-out explodes.

**Responsibilities**

- Accept posts and follows; store posts durably in the **Post store**, edges in the **Follow graph store**.
- Fan each post out asynchronously — **Feed API** → **Fan-out queue** → **Fan-out workers** → **Timeline cache** — hitting a ~5-second freshness target.
- Serve `GET /feed` as a cheap read: precomputed IDs, hydrated to content, merged with live celebrity posts.

The defining decision is the **hybrid**: push for the many (~200 followers), pull for the huge (100M+ followers, whose posts skip fan-out and merge at read time).

**Where it breaks.** The timeline is derived data with no reconciliation — a worker crash mid-fan-out would silently lose deliveries, which is why the pipeline pairs at-least-once redelivery with idempotent inserts. And staleness lives in the queue: fan-out lag *is* the user-visible SLO.

---
title: User
kind: Actor
technology: Human · HTTPS
---

## 👤 User

The **User** is the only actor in the model, and they generate both sides of the fan-out arithmetic: they *post* (rarely — 5,800 posts/s across the whole system) and they *read their feed* (constantly — 2 million feed queries/s when 10M concurrent users poll every 5 seconds). That asymmetry, roughly 400:1 in favor of reads, is why the system does its expensive work at write time.

**Responsibilities**

- Create posts (`POST /posts`) — each one becomes ~200 timeline writes downstream, on average.
- Follow other users — a uni-directional edge that decides whose posts land in their feed.
- Read the home timeline (`GET /feed`), paging back with a cursor.

Everything reaches the system over HTTPS through the **Feed API**; the user never sees the queue, the workers, or the caches behind it.

**Where it breaks.** Users are also the design's consistency oracle: the one anomaly they reliably notice is *their own* post missing after a reflex refresh — the read-your-writes gap the lesson's third deep dive exists for. And the tail of this actor population (accounts with 100M+ followers) is what forces the hybrid: designing for the *average* user is the trap.

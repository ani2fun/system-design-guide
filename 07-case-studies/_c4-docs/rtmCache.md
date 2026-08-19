---
title: Event & seat-map cache
kind: Cache
technology: Redis
---

## ⚡ Event & seat-map cache

The **Event & seat-map cache** carries the volume side of the 100:1 read skew: event details, venue information, performer bios, seat-map geometry — data written once and read millions of times, the friendliest workload caching gets.

**Responsibilities**

- Serve event pages to the **browse service** keyed `eventId → event object`, read-through: miss → Postgres → populate.
- Hold long TTLs on static fields, with invalidation triggered from the database when an event actually changes.
- Absorb what would otherwise be millions of identical queries hammering the transactional store during an on-sale — the same store the booking path needs healthy.

The deliberate word in the model is **seconds-stale**: outside checkout, a browse page that lags reality by a few seconds costs nothing, so the cache is allowed to lie a little in exchange for keeping reads off Postgres.

**Where it breaks.** The one thing this cache must *not* serve lazily is **seat availability** — that is the real-time surface, and it belongs to the SSE push channel (and, during extreme on-sales, behind the waiting room). A designer who caches the seat map with a lazy TTL rebuilds the exact demoralizing-blur failure the admission-control dive exists to prevent: two hundred fans clicking a seat that sold seconds ago. The split to keep sharp: static details from cache; availability pushed, or read with TTLs measured against how fast seats actually move.

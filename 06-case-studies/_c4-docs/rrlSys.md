---
title: Rate Limiter
kind: System
technology: Gateway middleware + Redis counter state
---

## 🏢 Rate Limiter

The **Rate Limiter** is an infrastructure *component*, not a product: one decision — `allow(key)?` — made a million times a second, correctly under concurrency, in under 5 ms per check. Everything inside it exists because the naive hash-map-and-if-statement dies three deaths in production: per-node counters make a 100/minute limit worth 100 × the server count (**counters must be shared, not local**); process memory zeroes on every deploy; and a concurrent read-then-write **loses updates** on exactly the load it exists to control.

**Responsibilities**

- Check every request at the edge — inside the **API gateway**, before any application code runs — so denied traffic never costs the backends anything.
- Resolve which rule applies (per-user, per-IP, per-endpoint, most-restrictive wins) from a locally cached **rule store**.
- Run the check as **one atomic round-trip** to shared Redis **counter state**: a Lua script reads, refills, decides, and writes as a single indivisible step, closing the lost-update race.
- Answer denials with 429 + `Retry-After` and the `X-RateLimit-*` headers — fail fast, never queue.

**Where it breaks.** The limiter is coupled to the platform's worst moments: Redis failures *correlate* with traffic spikes, which is why this design **fails closed** — brief rejections beat pouring a flood onto drowning backends — with an alert on entering the degraded mode, because a limiter that silently stopped limiting looks healthy until the backends fall over.

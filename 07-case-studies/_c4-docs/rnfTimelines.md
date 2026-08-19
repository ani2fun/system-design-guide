---
title: Timeline cache
kind: Cache
technology: Redis
---

## ⚡ Timeline cache

The **Timeline cache** is what *"precomputed feed"* physically is: per-user, time-ordered, capped lists of **post ids** — a materialized view of the posts⋈follows join, kept current by the fan-out pipeline. It is the reason a feed read is one key lookup instead of a 200-account query.

**Responsibilities**

- Absorb ~1.16M small prepends/second from the **fan-out workers** — the write side of push-based fan-out.
- Serve `userId → id list` to the **feed API** for every `GET /feed`; the API hydrates ids into content separately.
- Cap each timeline at ~200 entries. Ids, not text: at ~10 bytes per id that's ~2 KB per user and single-digit terabytes across 2B users — trivially affordable, which is the point. Storing content would balloon storage and go stale instantly (like counts and avatars mutate constantly).

The cap has an honest consequence: page far enough back and the materialized feed simply *ends*. The fallback is the design's own history — the pull path, querying follows + posts directly — and it can be slow in peace, because almost nobody pages that deep.

**Where it breaks.** This store is **not a ledger**. It is best-effort derived data whose SLO is freshness, not completeness: a delivery missed without redelivery is permanently invisible (nothing downstream reconciles), and for hyper-followers the design deliberately drops writes and shows a sample. Correctness therefore lives in the pipeline feeding it — at-least-once delivery plus idempotent inserts — not in the store itself. Losing a node means rebuilding timelines from the pull path, not restoring a backup.

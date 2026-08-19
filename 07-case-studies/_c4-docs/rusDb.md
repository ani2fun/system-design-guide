---
title: Link store
kind: Relational database
technology: PostgreSQL
---

## 🗄️ Link store

The **Link store** is the system of record: one table of `code → long URL` rows (plus creation time, optional expiration and alias, creator), with a unique index on the code. The hot path touches exactly one entity — no joins, no cross-entity transactions — so every lookup is a primary-key point read, the cheapest question a database answers.

**Responsibilities**

- Persist every mapping durably; serve as the source of truth the cache is filled from.
- Serve the read path's *miss* traffic — the small fraction of redirects the cache doesn't absorb.
- Accept new-link inserts, where the unique index on `code` is the last line of defense for the uniqueness requirement.

The numbers here are the design's most counterintuitive lesson. One billion rows at ~500 bytes is **~500 GB** — a dataset one modern node holds without noticing — and writes arrive at roughly **one per second**. So there is no sharding and no write-scaling machinery; proposing them is the classic estimation mistake on this problem. What the store *does* need is redundancy and read headroom: leader–follower replication with reads on followers, because 99.99% availability forbids a single copy and misses still have to land somewhere.

**Where it breaks.** Replication lag, in one user-visible way: create a link, share it instantly, and the first click may hit a follower that hasn't seen the row — a 404 on a brand-new link. The one-line fix lives upstream: populate the redirect cache at creation time. The other pressure point is a cold viral key stampeding the miss path — also blunted by that same write-time fill, since links go viral young.

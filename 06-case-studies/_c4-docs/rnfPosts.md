---
title: Post store
kind: Relational database
technology: PostgreSQL
---

## 🗄️ Post store

The **Post store** is the system of record for posts: `id → author, content, timestamp`. Everything else that holds post data — every entry in every materialized timeline — is a derived copy; this table is the source they derive from.

**Responsibilities**

- Accept post inserts from the **Feed API** write path. Write volume is the easy part of this design: 5,800 posts/s on average is a modest load for a partitioned relational store.
- Serve **hydration** — timelines store only post IDs, so every feed read comes back here to turn ~200 IDs into content. This is a read-time join by design: post bodies, like counts, and author profiles change too fast to denormalize into 200 follower timelines apiece.
- Serve the **CelebrityMerger**'s live queries for recent posts by flagged high-follower accounts — celebrity posts live *only* here, never fanned out.

The reasoning for IDs-then-hydrate: hydration cost is bounded (~a page worth of lookups, parallelizable, independent of anyone's follower count), whereas the join it replaced — across all followed accounts — was unbounded.

**Where it breaks.** Hydration means every feed read in the system lands here, so the store lives or dies by its cache hit rate; a hot celebrity post is the classic hot-key. It is also the recovery root: a lost timeline is rebuildable from posts + follows, but a lost post is gone.

---
title: Follow graph store
kind: Relational database
technology: PostgreSQL
---

## 🗄️ Follow graph store

The **Follow graph store** holds the follower/followee edges — a many-to-many relationship that the system must query in *both* directions, which is the whole subtlety of this box.

**Responsibilities**

- Store one row per uni-directional follow edge, inserted when a user follows someone (an idempotent `PUT` — following twice is a no-op).
- Answer **"who follows X?"** for the **Fan-out workers**: every post event triggers a follower-list read here, and that list *is* the fan-out — its length (~200 on average, 100M+ in the tail) decides how much work one post becomes.
- Answer **"whom does X follow?"** for the read-path fallback and the celebrity merge — the reader's own follow list identifies which flagged accounts to live-query.

Both directions need an index; the lesson models it as a table keyed one way with a reversed secondary index. The *distribution* stored here is the design input: the hybrid exists because this graph's follower counts have a monstrous tail, and the celebrity flag is effectively an attribute of an account in this graph.

**Where it breaks.** The follower-list read sits on the critical path of every fan-out job — a slow read here stalls delivery lag directly. And new edges only affect *future* posts: follow someone today and your materialized timeline knows nothing about their back catalog until a backfill or read-time patch fixes it.

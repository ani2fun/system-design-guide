---
title: Orders DB
kind: Relational database
technology: PostgreSQL
---

## 🗄️ Orders DB

The **Orders DB** is the system of record and the last word on the only invariant that matters: one `sold` transition per seat, ever. Everything upstream — waiting room, holds, payment — is choreography; this container is the arbiter.

**Responsibilities**

- Hold the ticket-per-seat rows — the schema decision that matters most, because pre-creating a row per bookable seat is *materialized conflict*: it collapses what would be a phantom/write-skew race (guarding on the absence of rows) into an ordinary, lockable single-row conflict. Every fight has an address.
- Execute the confirm as a short transaction with explicit pessimism: `SELECT … FOR UPDATE` on the seat rows, a conditional transition from `available` to `sold`, the order row written in the same commit.
- Reject the loser: a racing confirm — or a zombie whose hold expired mid-GC-pause — matches zero rows, and that zero *is* the fence. Conditional atomic writes stand in for fencing tokens.

The isolation stance is deliberate: **read committed plus hand-placed locks**, not `SERIALIZABLE`. Optimistic serializable control aborts and retries under contention, and an on-sale is the high-contention worst case — pessimism on exactly the contended rows pays for coordination only where the fight lives.

**Where it breaks.** Long transactions. The classic trap is stretching the row lock across the five-minute human checkout — pinned connections, deadlocks, stranded locks. Locks here are for milliseconds; think-time lives in the TTL hold store. Keep confirms short and this container scales further than intuition suggests, because ~50k rows per event is small — it's *hot*, not big.

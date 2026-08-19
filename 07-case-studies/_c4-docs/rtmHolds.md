---
title: Seat-hold store
kind: Cache
technology: Redis
---

## ⚡ Seat-hold store

The **Seat-hold store** holds one small fact per contested seat — `seat → holder`, with a TTL — and that TTL is the whole reason it exists. A hold is a **lease**, not a lock: it expires on its own, so a shopper who wanders off, a browser that crashes, or a booking server that dies mid-checkout all free the seat automatically. No sweeper job, no expired-row clutter, no correctness hostage to a scheduler.

**Responsibilities**

- Grant a hold atomically — set-if-not-exists with a ~10-minute TTL (`SET NX PX`) — so two fans clicking seat 22A in the same instant get exactly one winner.
- Store the holder's identity as the value, so confirm can verify the right user is completing.
- Expire silently; drop the key on explicit release after purchase.

Why not keep holds in Postgres rows? Because on-sale **hold churn** — grab-and-abandon attempts vastly outnumbering sales — would land on the transactional tables that must stay short-transaction-fast. Churn lands on memory instead; the ticket table shrinks back to `available | sold`.

**Where it breaks.** Leases lie: a GC-paused server can resume believing it still holds an expired hold (the zombie), and a Redis failover onto an async replica can forget recent grants entirely. Both are survivable *by design* — the final sale is the conditional, row-locked write in the orders DB, which insists the row still be sellable regardless of what any lease claims. Lose every hold and shoppers race, some losing at the payment page: degraded UX, **zero double-sells**. Never promote this store to arbiter.

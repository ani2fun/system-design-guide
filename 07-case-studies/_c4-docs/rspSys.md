---
title: Payment System
kind: System
technology: At-least-once + idempotent · event-sourced ledger
---

## 🏢 Payment System

The **Payment System** is the case study where the escape hatches run out: the data *is* money, every record is a legal fact, and *"we lost a little under load"* is a regulator's opening question. Its contract fits in one line: **a payment may be slow; it may never be wrong.** Notice what the non-functional requirements *don't* ask for — low latency on the final outcome. The system deliberately spends timeliness (pending states, day-late settlement, batch reconciliation) to buy absolute integrity.

**Responsibilities**

- **Never charge twice**: retries are mandatory (a timeout tells the caller nothing) *and* lethal (a duplicate charge is data corruption with a customer attached), so every mutating call is idempotent end-to-end via merchant-supplied keys.
- **Never lose a charge**: a timeout is not a failure — it is the absence of knowledge, held honestly in a first-class `pending_verification` state until the PSP's late-arriving truth resolves it.
- **Never UPDATE money**: every movement is append-only double-entry ledger postings; balances are derived views, deletable and recomputable; refunds and corrections are new opposite entries, never edits.
- **Trust, but verify**: a reconciliation job diffs our ledger against the networks' settlement files and surfaces every break instead of absorbing it.
- Handle ~10,000 TPS at peak with bursty holiday traffic, auditable forever.

**Where it grows.** The append-only core is the scaling gift: logs absorb write bursts better than update-in-place tables, and every read-side view is a rebuildable cache. The bottleneck that remains is the external one — the card rails answer at their own pace, which no amount of our hardware changes.

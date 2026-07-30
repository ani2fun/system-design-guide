---
title: Ledger
kind: Relational database
technology: PostgreSQL (append-only)
---

## 🗄️ Ledger

The **Ledger** is the financial source of truth auditors read — a double-entry record where every movement of money is a set of immutable entries summing to zero: a $50 capture debits customer funds $50 and credits the merchant's pending balance $50. The intuition section's villain was the mutable balance column, whose `UPDATE` destroys history; this table is the refusal to ever run `UPDATE` on money again — enforceable at the database-permission level with insert-only grants.

**Responsibilities**

- Accept **appends only**. A refund is not an edit — it is new entries in the opposite direction under a new Refund transaction. An operator correction is likewise a new reversing entry. There is no `UPDATE` or `DELETE` path at all.
- Reject unbalanced postings: every transaction's entries must sum to zero, which is what *"no money lost, none conjured"* means mechanically.
- Serve as the base for **derived balances**: a balance lives nowhere authoritative — it is `SUM(entries WHERE account = X)`. At scale you materialize that sum from the CDC stream, but the materialization is a cache, always reconstructible; if a bug corrupts it, delete it and re-derive. In the naive design the corrupted balance *was* the record.
- Double as the audit log — event sourcing wearing an accountant's visor: replaying the same log reproduces the same state, so the system can *prove* what right is, not just be told it's wrong.

**Where it grows.** Append-only logs absorb write bursts better than update-in-place tables — the Black Friday shape of this traffic — while every read view catches up downstream at its own pace.

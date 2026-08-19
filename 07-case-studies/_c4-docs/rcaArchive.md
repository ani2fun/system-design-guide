---
title: Raw archive
kind: Object storage
technology: S3-style object store
---

## 🪣 Raw archive

The **Raw archive** is every click, untouched, forever cheap — the source of truth the batch path recomputes from. Its power comes from a property decided at ingest: click events are **immutable**. An event records that something *happened*; it is never updated, only appended — which is exactly what makes the archive replayable and auditable. Everything downstream of the log is a derived view, and derived views earn their trustworthiness from the ability to be *re*-derived: same input, fixed code, correct output. The archive is where that ability lives beyond the stream's 7-day retention.

**Responsibilities**

- Receive raw click events dumped from the stream path and keep them as the durable, append-only record — ~10 GB/day at 100M clicks, a rounding error against the reconciliation value it buys.
- Feed the reconciliation job's periodic from-scratch recomputation, and any ad-hoc replay: a bad deploy becomes a re-run instead of an apology.
- Anchor billing disputes: an advertiser challenging an invoice triggers a procedure — replay Tuesday's events, recompute, compare — not a negotiation. Signed impression IDs in the raw events let you check dedup, fabrication, and timeline gaps after the fact.

**Where it breaks.** The archive is only as good as what reaches it: it can prove or disprove anything about events it holds, and arbitrate nothing about clicks that were never captured. That's why the append-only, immutable log discipline is the one thing this design never compromises — integrity violations upstream of the archive are the ones no audit can repair.

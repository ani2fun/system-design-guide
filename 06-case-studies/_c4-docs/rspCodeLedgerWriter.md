---
title: LedgerWriter
kind: Code
technology: Python
---

## 🧩 LedgerWriter

**LedgerWriter** owns `post(entries)` — the only code allowed to touch the ledger, and the narrowest class in the system by design. It receives the postings a state transition implies (a $50 capture: debit customer funds $50, credit merchant pending balance $50; in the full model a third pair carves out the processing fee) and appends them atomically. It is the executable form of the lesson's deepest fix: `UPDATE` destroys history, so money is never UPDATEd again.

**Responsibilities**

- **Reject any posting set that doesn't sum to zero** before writing — balance is checked at the door, not hoped for downstream.
- **Append, only ever append**: a refund is new entries in the opposite direction under a new transaction; an operator correction is a new reversing entry. No update or delete path exists — enforceable below the application with insert-only database grants.
- Leave balances to the readers: a balance is a derived view, `SUM(entries WHERE account = X)` — materialized from the CDC stream at scale, but always a deletable, recomputable cache, never the truth.

**The invariant it maintains:** **entries always balance, and the ledger is never UPDATEd** — no money lost, none conjured, mechanically. That pair is what makes the reconciliation job's audit possible: an append-only log can be replayed to *prove* what right is, where a mutable balance could only be overwritten and the bug's damage made permanent.

**Where it breaks.** Nothing here dedupes or sequences — LedgerWriter trusts that IdempotencyGuard and PaymentIntentMachine ran first. Called outside that order, it will faithfully append a balanced double charge. Lands in the forthcoming POC at `06-case-studies/examples/stripe-payments/app/ledger_writer.py`.

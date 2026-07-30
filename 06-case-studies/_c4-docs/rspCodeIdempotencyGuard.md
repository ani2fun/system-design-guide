---
title: IdempotencyGuard
kind: Code
technology: Python
---

## 🧩 IdempotencyGuard

**IdempotencyGuard** owns `run(key, request, fn) Result` — the front door of the payment API's write path. It wraps every mutating operation: look the key up first; if it's new, record it and execute `fn` (the real work — state machine, PSP call, ledger postings); if it's seen, execute nothing and **replay the stored result**. It runs first because retries are mandatory — a timeout tells the merchant nothing about whether the charge happened — and lethal, since executing a charge twice is data corruption with a customer attached.

**Responsibilities**

- Insert the key under a **uniqueness constraint on (merchant_id, key)** in the *same transaction* that records the attempt — a duplicate's `INSERT` aborts cleanly; no check-then-insert race.
- Store key → **outcome** (status and body), so a retry receives exactly what the original produced — even mid-flight, when the honest answer is `409 processing`.
- Fingerprint the request, so the same key with a *different* payload is rejected as a client bug rather than replayed.

**The invariant it maintains:** **same key ⇒ same outcome, end-to-end.** This is the end-to-end argument in code — duplicate suppression can only be implemented with the help of the endpoints. TCP dedupes within one connection; the database transaction is atomic but can't link a reconnecting client's retry to the commit it never saw. Only a client-generated ID carried through every hop to a uniqueness check suppresses the duplicate — including the user double-clicking checkout.

**Where it breaks.** Key expiry: a retry arriving after the retention window is a new operation. Lands in the forthcoming POC at `06-case-studies/examples/stripe-payments/app/idempotency_guard.py`.

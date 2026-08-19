---
title: Idempotency key store
kind: Relational database
technology: PostgreSQL
---

## 🗄️ Idempotency key store

The **Idempotency key store** is the memory that makes retries safe: `key → (request fingerprint, stored result)`. It exists because of the uncomfortable pair of facts the lesson opens with — in a distributed system retries are not optional (a timeout gives the merchant zero information), and in a payment system a blind retry is the worst bug you can ship. This table is where "encouraged *and* harmless" is enforced.

**Responsibilities**

- Hold a **uniqueness constraint on (merchant_id, idempotency_key)** — inserted in the *same database transaction* that creates the payment attempt, so a retry's `INSERT` violates the constraint and aborts cleanly instead of charging again. Relational uniqueness holds even at weak isolation levels, where hand-rolled check-then-insert falls to write skew.
- Scope keys **per merchant** (two merchants may coincidentally generate the same UUID) and per endpoint — the scope must exactly equal *"one logical operation from the client's point of view."*
- Store the **response**, not just the key: a retry receives the same status and body the original produced, even mid-flight (`409 processing`) — key → outcome is a response cache with a legal function.
- Expire keys after a retention window (rule of thumb: ~24 hours) — the table can't grow forever at 10k TPS.

**Where it breaks.** At the edges of its own guarantees: a retry arriving *after* expiry is indistinguishable from a new operation, and the store only protects the merchant→us hop — the us→network hop needs its own attempt-reference discipline, because exactly-once is renegotiated at every trust boundary.

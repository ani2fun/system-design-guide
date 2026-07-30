---
title: Payment intents DB
kind: Relational database
technology: PostgreSQL
---

## 🗄️ Payment intents DB

The **Payment intents DB** holds the state machine's event log per payment: every transition — created, authorized, captured, settled, refunded, disputed — is an appended event, and the intent's current *"status"* is merely a fold of its history. A PaymentIntent answers *"what does the merchant want?"* — one intent, one *"please collect $50,"* no matter how many attempts that takes; each attempt is a separate Transaction row referencing back to it, which is what makes a retry representable at all.

**Responsibilities**

- Append state events; never rewrite them — the past-tense record of what happened is the audit trail regulators read.
- Hold `pending_verification` as a **first-class state**: a timeout is not a failure, it is the absence of knowledge, and the machine must be able to say *"I don't know yet"* without lying in either direction. The PSP's truth arrives late — via webhook or reconciliation — and only then does the pending state resolve.
- Keep `settled` distinct from `captured`: authorization and capture are messages; settlement is *money*, moving in a batch days later. Conflate them and you report money as arrived that a network failure still owes you.
- Feed CDC: every committed change is captured off the write-ahead log into Kafka, keyed by `payment_intent_id` for per-intent ordering — the eventing is automatic, not disciplinary.

**Where it breaks.** If application code could flip a status column directly, illegal transitions would be merely discouraged. The PaymentIntentMachine class exists to make them impossible — this store is only as trustworthy as that single write path.

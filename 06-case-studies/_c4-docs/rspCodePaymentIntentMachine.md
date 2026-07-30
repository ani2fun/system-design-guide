---
title: PaymentIntentMachine
kind: Code
technology: Python
---

## 🧩 PaymentIntentMachine

**PaymentIntentMachine** owns `transition(intent_id, event) State` — the single legal way a payment's lifecycle moves. It encodes the graph from the lesson: created → processing → authorized → captured → settled, with exits to failed, canceled, refunded, and disputed — and, crucially, `processing → pending_verification` on timeout, because a timeout is *not* a failure; it is the absence of knowledge, and the machine must be able to say *"I don't know yet"* without lying in either direction. Only IdempotencyGuard's first-attempt path reaches it; retries never do.

**Responsibilities**

- Validate every requested transition against the legal-transition table and **reject illegal ones structurally** — `settled` cannot come from `created`; a decline cannot follow a capture.
- **Append an event per transition**, past tense, to the intents DB; the *"current status"* is never stored authoritatively, only derived.
- Keep `settled` distinct from `captured`: authorization and capture are messages; settlement is money moving in a batch days later.
- Hand each completed money-moving transition to LedgerWriter as balanced postings.

**The invariant it maintains:** **illegal transitions are impossible, not discouraged — and state = fold(events).** Any reader folding the same event history reaches the same status; there is no column a bug or an operator can flip out from under the history. When the PSP's late truth arrives by webhook or reconciliation, it lands as one more appended event resolving `pending_verification` — never an edit.

**Where it breaks.** Any second write path to the status column dissolves the guarantee — the machine only protects transitions that go through it. Lands in the forthcoming POC at `06-case-studies/examples/stripe-payments/app/payment_intent_machine.py`.

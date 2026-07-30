---
title: PaymentClient
kind: Code
technology: Python
---

## 🧩 PaymentClient

**PaymentClient** is the booking service's boundary with the outside world: the external payment provider, reached over a network that times out, retries, and delivers webhooks late.

**Responsibilities**

- `capture(amount, idempotency_key)`: authorize and capture the charge against the PSP, carrying **one idempotency key per checkout attempt** so a retried request can never become a second charge.
- Surface the PSP's asynchronous reality to the caller: a timeout is *unknown*, not *failed* — the charge may have landed — and the webhook, not the synchronous response, is often the truth.

The idempotency key is the whole design of the class. Payment calls sit on the wrong side of a network partition from your transaction: you cannot atomically *"charge the card and mark the seat sold."* What you *can* do is make the charge safely repeatable — same key, same attempt, at most one capture — and let `BookingConfirmer`'s conditional write arbitrate the seat regardless of when the payment confirmation arrives. The lesson's sequence shows the payoff: a webhook that lands *after* the hold expired meets a conditional update that matches zero rows — refund and apologize, never double-sell.

**The invariant it protects:** one checkout attempt produces **at most one capture**, however many times the request is retried or the webhook redelivered.

**Where it breaks.** Reusing a key across *different* attempts (new seat, new price) silently returns the old result; minting a fresh key per retry silently double-charges. Key scope is the bug surface. Stubbed in the forthcoming POC at `06-case-studies/examples/ticketmaster/app/payment_client.py`.

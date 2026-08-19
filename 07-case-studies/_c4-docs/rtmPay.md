---
title: Payment provider
kind: External system
technology: External PSP (e.g. Stripe)
---

## 🌐 Payment provider

An external **payment service provider** (PSP). The booking service authorizes and captures the card here during checkout; confirmation arrives back **asynchronously as a webhook** — and webhooks redeliver.

**Responsibilities**

- Charge the card for a checkout attempt when the booking service calls authorize/capture.
- Deliver a payment-succeeded webhook that triggers the final confirm transaction.
- Honor **idempotency keys**: the PaymentClient sends one key per checkout attempt, so a retried capture is a no-op rather than a double charge.

The PSP sits *outside* the correctness boundary on purpose. Payment success does not sell the seat — the confirm transaction in Postgres does, and it re-checks that the ticket row is still sellable before marking it sold. That ordering matters because the PSP's timing is not yours: a webhook can arrive minutes late, after the shopper's ten-minute hold has already expired and the seat has gone to someone else.

**Where it breaks.** Exactly there: a late webhook for an expired hold hits the conditional `UPDATE`, matches 0 rows, and the confirm fails cleanly — refund and apologize, never double-sell. The production sin to avoid is a webhook handler that emails, increments, or charges *outside* that guarded transaction; redelivery then duplicates the side effects even though the sale itself stays correct.

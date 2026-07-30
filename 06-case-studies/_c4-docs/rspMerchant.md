---
title: Merchant
kind: Actor
technology: Business backend · REST + webhooks
---

## 👤 Merchant

The **Merchant** is a business's backend server calling our API to charge its customers — and the design's first hard truth lives on their side of the wire: when a call times out, the merchant learns *nothing* about whether the charge happened, so any correct client **must retry**. The system is built so that this mandatory retry — which in a payment system would otherwise be the worst bug you can ship, a double charge — is harmless.

**Responsibilities**

- Generate a unique **idempotency key** per logical operation (a UUID or an order hash) and send it in the `Idempotency-Key` header on every mutating call — `POST /payment-intents`, `POST /payment-intents/{id}/confirm`.
- **Reuse the same key on every retry** — the key is what lets our side recognize the retry as the same operation and replay the first outcome instead of charging again.
- Never touch raw card data: the customer's browser sends card details to our hosted iframe directly; the merchant's server only ever handles an opaque token (PCI DSS).
- Consume outcomes two ways — polling `GET /payment-intents/{id}` and receiving our **signed webhooks** — and deduplicate webhook deliveries by event ID, because we deliver at-least-once.

The load-bearing habit is patience: a `processing` status is not an error, because the truth from the card networks arrives late by design.

**Where it breaks.** A merchant that generates a *fresh* key per retry defeats the entire duplicate-suppression machinery — the end-to-end argument says the ID must originate where the operation is logically one thing, and that place is the merchant's code.

# POC: Payment System (Stripe-style)

A runnable implementation of the **Design a Payment System** case study
(`06-case-studies/12-stripe-payments`) — never charge twice, never lose money,
auditable forever.

The three classes under [`domain/`](domain/) mirror the C4 code elements 1:1:

| C4 code element | File | Role |
| --- | --- | --- |
| `IdempotencyGuard` | [`domain/idempotency_guard.py`](domain/idempotency_guard.py) | same key ⇒ same outcome; replay the first attempt |
| `PaymentIntentMachine` | [`domain/payment_intent_machine.py`](domain/payment_intent_machine.py) | created → authorized → captured → settled; illegal transitions raise |
| `LedgerWriter` | [`domain/ledger_writer.py`](domain/ledger_writer.py) | append-only double-entry postings that sum to zero |

The whole charge is one transaction via the `PaymentUnitOfWork` port; the
Postgres adapter's idempotency-key insert is what makes it exactly-once even
across concurrent retries.

## Run it

```bash
./run            # build + start api (8420) + Postgres (8421)
./run test       # mypy --strict + smoke
./run stop
```

## What the smoke proves

- **Idempotency** — charging with the same key twice returns the *same* payment
  and the merchant is credited **once**.
- **Concurrent retries** — 10 charges of one key fired at once produce **one**
  payment (the second insert blocks on the unique key until the first commits,
  then replays the stored result).
- **State machine** — `created → capture` is rejected (409); `created →
  authorize` is allowed. A payment can't reach a state it can't legally be in.
- **Double-entry** — every money movement is two postings that net to zero; the
  whole ledger sums to **0**.

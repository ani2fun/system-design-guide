---
title: BookingConfirmer
kind: Code
technology: Python
---

## 🧩 BookingConfirmer

**BookingConfirmer** is the critical section — the one place in the platform where *"never sell a seat twice"* is actually enforced.

**Responsibilities**

- `confirm(seat, user)`: open a short Postgres transaction, take the seat row's lock (`SELECT … FOR UPDATE`), re-verify the caller still holds the seat, transition it `available → sold` *conditionally*, write the order row, commit.
- Trigger `PaymentClient.capture` only on a confirm that can succeed, and treat a zero-rows-matched conditional write as the rejection it is — refund path, not retry path.

The conditional write is doing fencing-token work: a zombie whose Redis hold expired during a GC pause can still arrive here, but its `UPDATE … WHERE status = 'available'` matches nothing once another buyer owns the row. Storage that supports conditional atomic writes replaces fencing tokens — the compare-and-set *is* the fence.

**The invariant it protects:** the row-lock transaction is the **final arbiter** — exactly one `sold` transition per seat row, no matter what any hold, cache, or delayed webhook claims. Redis losing every hold produces races and apologies, never a double-sell.

**Where it breaks.** Turn the pessimism off and watch: the class carries a `use_locking` flag so the forthcoming POC (at `06-case-studies/examples/ticketmaster/app/booking_confirmer.py`) can demonstrate that without the lock, two concurrent confirms both read `available` and both sell the seat. The flag is pedagogy — the lock is not optional in production, and neither is keeping the transaction milliseconds short.

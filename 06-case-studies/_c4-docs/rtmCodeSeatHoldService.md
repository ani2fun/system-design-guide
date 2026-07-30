---
title: SeatHoldService
kind: Code
technology: Python
---

## 🧩 SeatHoldService

**SeatHoldService** manages the checkout's admission ticket: the per-seat, per-user TTL hold in Redis.

**Responsibilities**

- `acquire(seat, user, ttl)`: one atomic set-if-not-exists with expiry (`SET NX PX`) — two fans racing for the same seat get exactly one winner, decided by Redis's single-threaded execution, no application-level check-then-set window.
- `holder(seat)`: report who holds a seat, so the confirm step can verify the completing user is the one who held it.
- `release(seat, user)`: drop the hold on success or explicit abandonment; otherwise the TTL fires and the seat frees itself.

The class is small because the design pushed all the hard guarantees elsewhere. It deliberately does **not** try to be a correct distributed lock — no fencing tokens, no consensus — because the lesson's layering makes that unnecessary: the hold is the *experience* (a humane checkout where your seat won't vanish mid-payment), while the *invariant* belongs to `BookingConfirmer`'s row-locked transaction.

**The invariant it protects:** at most one live holder per seat at any instant, and no hold outlives its TTL — so crashed or abandoned checkouts release inventory automatically, without a sweeper.

**Where it breaks.** The lease that lies: a GC pause can leave a caller acting on a hold that already expired, and an async Redis failover can forget grants. Both degrade UX only — the conditional confirm downstream fences the consequences. Implemented in the forthcoming POC at `06-case-studies/examples/ticketmaster/app/seat_hold_service.py`.

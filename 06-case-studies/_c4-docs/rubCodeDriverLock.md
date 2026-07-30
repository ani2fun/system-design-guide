---
title: DriverLock
kind: Code
technology: Python
---

## 🧩 DriverLock

**DriverLock** is the offer-window lease: one atomic `SET NX PX` per driver — Ticketmaster's `SeatHoldService` wearing a different hat, with the hold window shrunk from ten minutes to ten seconds and the inventory now driving around.

**Responsibilities**

- `acquire(driver_id, request_id, ttl)`: set `lock:driverId → rideId` only if absent, with expiry — two matchers racing for the same driver get exactly one winner, decided by Redis's atomic set, no check-then-set window.
- `release(driver_id, request_id)`: drop the lock on accept or explicit decline; otherwise do nothing — expiry handles it.

**The invariants it protects:** a driver holds at most **one outstanding offer at a time**, and no lock outlives its TTL — so a matcher that crashes mid-offer releases its driver by *expiry, not cleanup code*. Crashed flows self-heal; there is no sweeper, no orphan-lock cron, no sweep-lag during which drivers sit invisible.

**And the one it deliberately doesn't:** this lock is **advisory, not final**. It is a lease, and leases lie — a GC-paused matcher can resume after its TTL as a zombie leaseholder, so it is not safe to assume only one holder at any instant. The class carries no fencing tokens and no consensus, because the design puts the real guarantee elsewhere: the conditional trip write in Postgres is the final arbiter, and a zombie's late assignment matches zero rows. Lose this class entirely and drivers get messy duplicate offers — never double-booked.

**Where it breaks.** Exactly at that seam: anyone who treats `acquire` returning `True` as proof of exclusive assignment has rebuilt the bug the layering exists to prevent. Lands in the forthcoming POC at `06-case-studies/examples/uber/app/driver_lock.py`.

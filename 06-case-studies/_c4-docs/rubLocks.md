---
title: Driver locks
kind: Cache
technology: Redis (SET NX PX)
---

## ⚡ Driver locks

One key per driver, `SET NX PX`: the **offer-window lock** that guarantees a driver receives exactly one offer at a time. It's Ticketmaster's seat hold wearing a different hat — same atomic acquire, same TTL release — and it beat two rivals to get here. A lock in matcher memory fails on arrival: instances don't share memory, so two matchers can both *"lock"* driver A, and a crash strands the driver. A status column in Postgres fixes coordination but breaks *release* — the 10-second expiry lives in an in-memory timer, so a dead process locks the driver forever, patchable only with sweep-lag crons. The TTL lease moves release into the store itself.

**Responsibilities**

- Atomic acquire: set `lock:driverId → rideId` only if absent, TTL 10 s — two matchers racing for the same driver get exactly one winner.
- **TTL is the release**: accept in time and the matcher deletes the lock; silence, decline, or a crashed matcher, and expiry frees the driver unconditionally — no cleanup code, no sweeper.
- Stay **advisory**: the trip-creation transaction remains the final arbiter of who got the ride.

**Where it breaks.** A lease is not a guarantee: a paused matcher can outlive its TTL and resume as a zombie leaseholder, and a failover can forget grants. Both cost UX only — a stray duplicate offer for a few seconds — because the conditional trip write downstream fences the consequences. Lose this store entirely and you get messy offers, never a double-booked driver.

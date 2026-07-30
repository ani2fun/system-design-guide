---
title: Driver
kind: Actor
technology: Human · driver app, GPS on
---

## 👤 Driver

The **Driver** is two very different clients in one phone. As a *sensor*, the app streams a location ping every ~5 seconds all shift — across a fleet of roughly 10 million drivers, about 2 million writes per second of overwrite-only data that is worthless within seconds. As a *scarce resource*, the driver is the inventory being allocated: when a ride is offered, this driver must see **exactly one offer at a time**, with 10 seconds to accept or decline before the system moves on.

**Responsibilities**

- Stream location pings on a fixed interval while available — the firehose the Location service exists to absorb.
- Receive at most one offer at a time (enforced by the per-driver TTL lock) and answer it within the offer window; silence counts as decline.
- Accept or decline via the ride endpoint; an accept may be retried safely — assignment is idempotent downstream.

**Where it breaks.** This actor's phone is the least reliable component in the system: apps crash, batteries die, tunnels swallow signal. The design refuses to build a liveness protocol around that — a driver who stops pinging simply *ages out* of the geo index within one TTL, and an offer to a driver who went dark expires on its own lock TTL. Absence of evidence becomes evidence of absence, enforced by the data's own lifecycle.

---
title: Trip DB
kind: Relational database
technology: PostgreSQL
---

## 🗄️ Trip DB

The **Trip DB** is the system of record for the facts with a lifetime — riders, drivers, fares, trips and their state — everything the entity analysis kept *out* of the firehose path. It is deliberately boring: while location data gets an exotic in-memory store because of its write rate and shelf life, the durable facts arrive at human tempo (a trip transitions a handful of times over an hour) and demand exactly what a relational database sells — transactions, constraints, conditional writes.

**Responsibilities**

- Hold the trip row as the ride's single durable spine; every state transition in the design is ultimately a transition on this row.
- Enforce **one trip per request** via a unique constraint — the mechanism behind OfferFlow's exactly-once trip creation; a retried accept hits the constraint instead of creating a duplicate.
- Back the **conditional write** that is the design's true invariant: assign a driver only where the trip is still unassigned, so a zombie matcher acting on an expired lease matches zero rows.

The layering, said once more: everything upstream — geo index, TTL locks, offer pushes — is *experience*; this container is the *invariant*. Lose Redis and you get a few seconds of messy offers; lose the constraint here and you double-book drivers.

**Where it breaks.** Not on write volume — successful matches are a trickle next to the ping firehose — but on contention in hot zones, where thousands of concurrent transitions converge; the queue ahead of matching meters arrivals so its short transactions stay short.

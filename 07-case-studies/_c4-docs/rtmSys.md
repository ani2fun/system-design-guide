---
title: Ticketing Platform
kind: System
technology: Gateway + FastAPI services + Redis + PostgreSQL
---

## 🏢 Ticketing Platform

**Contention is the product**: N fans, 1 seat. The invariant — *never sell a seat twice* — decides the whole design, because at 10M users versus ~50k seats, over 99% of the crowd can't buy anything. This is really **two systems wearing one trench coat**, and keeping them apart is most of the architecture.

**Responsibilities**

- **The read-mostly catalog** (browse + search + cache) serves the 99%: event pages, seat maps, keyword search. Availability-biased, aggressively cached, allowed to be seconds-stale.
- **The contended transactional core** (booking + holds + orders) serves the few: strongly consistent, no double booking, coordination paid only on the rows where the fight is.
- **Admission control at the edge** (the waiting room) converts an uncontrollable stampede into a drain the core can sustain.

Note what is *not* hard here: write volume. Selling out a stadium is ~50k successful writes — a trickle. The problem is that they all aim at the same rows: **contention, not load**. So the split consistency posture is per-endpoint, not database-wide — availability for viewing, strong consistency for booking.

**Where it grows.** Each half scales on its own terms: the catalog horizontally (stateless services, cache, search index), the core by *narrowing* — shorter transactions, holds pushed to memory, admission throttled at the gate. Scaling the core by adding servers only multiplies transactions fighting over the same 50k rows.

---
title: Uber
kind: System
technology: Gateway + FastAPI services + Redis + PostgreSQL
---

## 🏢 Uber

**Geospatial matching under contention**: find nearby drivers fast, offer to exactly one, survive the hot zone. The architecture falls out of one observation about the entities — four of them (rider, driver, fare, ride) are *facts with a lifetime* that belong in rows; the fifth, driver location, is a **firehose**: written ~2M times a second, overwritten on every write, worthless when stale. Splitting those two lifetimes into different stores is most of the design.

**Responsibilities**

- **Absorb the firehose** on a dedicated write path: pings flow through the Location service into a TTL'd in-memory geo index — nothing durable ever sees them.
- **Allocate under contention**: the Matching service radius-queries candidates, takes a per-driver TTL lock so no driver gets simultaneous offers, and walks the ranked list one offer at a time.
- **Own the durable spine**: the Trip service runs the ride's state machine, with PostgreSQL as the system of record and the final arbiter of who got the ride.
- **Deliver in real time**: offers to drivers, live status to riders.

The layering to say out loud: **Redis is the experience; Postgres is the invariant.** TTLs make freshness and lock-release automatic; the conditional trip write makes *"one driver per ride"* true even if every lease lies.

**Where it breaks.** Hot zones — a stadium emptying concentrates riders and a knot of drivers into one geohash cell, textbook skew that uniform sharding cannot fix; the answers are queue-buffered matching, subdividing hot cells, and geographic partitioning so one city's meltdown stays local.

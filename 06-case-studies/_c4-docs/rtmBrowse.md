---
title: Browse & search service
kind: Service
technology: Python · FastAPI
---

## ⚙️ Browse & search service

The storefront for the 99% who never buy. With a ~100:1 read-to-write ratio, this path — not booking — carries the volume, and it's a friendly workload: event details are written once and read millions of times.

**Responsibilities**

- Assemble event pages — event, venue, performers, seat map — serving from the **cache** first (read-through: miss → DB → populate).
- Answer keyword search by delegating to the **search index**; never scan.
- Serve seat *availability* differently from static detail: availability is the one thing you must not cache lazily — it's pushed fresh (SSE deltas) or read with short TTLs, while venue geometry and bios take long TTLs.

The service is deliberately stateless: scale it horizontally behind the gateway, and let the cache absorb what would otherwise be millions of identical queries hammering Postgres. Its correctness bar is low by design — a browse page that's seconds stale costs nothing, because the booking path re-checks everything that matters.

**Where it breaks.** The *"Taylor Swift case"*: when seats sell in seconds, even flawless real-time seat-map updates deliver a blur of disappearing green — technically correct, experientially useless. Freshness alone can't fix a 200:1 demand ratio; that's the gateway's waiting room's job. Until then, this container's failure mode is the refresh storm: without the cache and push updates, 10M fans polling the seat map would flatten the database long before anyone books.

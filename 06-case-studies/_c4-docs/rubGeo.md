---
title: Geo index
kind: Cache
technology: Redis GEO
---

## ⚡ Geo index

The **Geo index** is the store shaped like the question: "who's nearby, *right now*?" `GEOADD` encodes each driver's lat/lng as a **geohash** — coordinates interleaved into one sortable value, so nearby points (edge cases aside) share prefixes — in a sorted set; `GEOSEARCH` answers radius queries directly against that structure. In-memory speed absorbs the full 2M-writes/second firehose with no batching, where a B-tree over `lat`/`lng` degenerates to scanning a latitude band, and a quadtree — right for skewed, *static* spatial data — churns endlessly under a swarm in motion. Geohash's fixed grid is indifferent to update rate, which is exactly why it wins here.

**Responsibilities**

- Hold each driver's latest position, overwritten per ping — never a history.
- Enforce **freshness by TTL**: an entry not refreshed within the window simply expires, so a crashed app or a tunnel removes its driver from matching with no health checker and no liveness protocol. Stale drivers evaporate.
- Answer the Matching service's radius queries as the candidate source.

**Where it breaks — and why that's fine.** It's volatile, and the design leans into it: persistence and failover exist, but a cold replacement node rebuilds the entire working set in one ~5-second ping interval, because the source of truth was never Redis — it's ten million phones. The honest costs are cell-boundary queries needing care, and hot cells (a stadium's geohash) concentrating load that uniform sharding can't spread — subdivide the hot cell instead.

---
title: NearbyDriverQuery
kind: Code
technology: Python
---

## 🧩 NearbyDriverQuery

**NearbyDriverQuery** answers the question that kills the naive design: "which available drivers are within *r* of this pickup, *right now*?" — as a `GEOSEARCH` against the geo index plus ranking (ETA, rating) over the hits. It is deliberately read-only and deliberately dumb about freshness.

**Responsibilities**

- `find(location, radius)`: radius query against the geo index, returning ranked candidates for the offer flow to walk.
- Rank, don't reserve: this class never touches locks or trips — it produces candidates; `DriverLock` and `OfferFlow` decide what happens to them.

**The invariant it relies on:** freshness comes from the **index TTLs, not from the query**. `find` never checks whether a driver is alive, recently seen, or still where the entry says — it doesn't have to, because any entry not refreshed within one ping interval has already evaporated. The class inherits liveness from the data's own lifecycle, which is why it can stay a single read with no health-check round-trips on the sub-minute matching path.

**Where it breaks.** Its answers are bounded-stale by construction — a candidate at ~50 km/h moves ~70 m between 5-second pings, noise against a kilometer-scale radius but real at pickup precision. And geohash cell boundaries can clip a radius query, so near-boundary searches need care. Both are accepted costs, not bugs: candidates are *offers to attempt*, and the lock + conditional trip write downstream absorb any staleness. Lands in the forthcoming POC at `06-case-studies/examples/uber/app/nearby_driver_query.py`.

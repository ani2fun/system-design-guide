---
title: CDN
kind: CDN
technology: CDN
---

## 🌍 CDN

The **CDN** is the honest answer to *"what serves the video?"* — not the API, not the rendition store, but edge caches near viewers. The design's extreme read asymmetry (100M watches against 1M uploads per day, with each watch streaming hundreds of segment files) is resolved by *placement*: writes and processing land on infrastructure we run; reads — 99%+ of all traffic — land on infrastructure whose entire job is being near users.

**Responsibilities**

- Cache **both segments and manifests** at the edge. Cache segments only and every playback on earth still hits the origin for its manifest fetches — the startup path must be edge-local too.
- Fill from the rendition store on miss, then serve every neighboring viewer from the edge.
- Serve static, shared objects over plain HTTP — nothing per-viewer, nothing computed.

That last point is load-bearing: the CDN can only do this job because *the server is dumb and the client is smart*. Every quality decision belongs to the player, so every object the CDN holds is identical for every viewer and therefore cacheable. A design that picks quality server-side breaks cacheability and un-invents the CDN.

For a hot video, the entire watch session — manifest fetches, every segment at every quality — is served edge-local, and the origin sees exactly one request: the metadata lookup.

**Where it breaks.** At the edges of its own economics: the first minutes of a viral video are fill traffic at every edge simultaneously, and the cold long tail is never cached anywhere — both land on the origin, which is precisely the residual duty it keeps.

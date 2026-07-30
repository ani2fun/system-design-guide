---
title: Edge cache
kind: CDN
technology: Cloudflare
---

## 🌍 Edge cache

The read path's real capacity. At the 1M-MAU peak the platform sees ~80 lesson loads/s — and ≥95%
of them terminate here, leaving the origin single-digit requests per second.

**Cache policy by asset class**

- **Page assets** — content-hashed filenames, cached as immutable.
- **Content JSON** — `max-age=60, stale-while-revalidate=600`, keyed against `contentVersion`
  (the content git SHA): one minute of author-visible staleness buys the read path's independence
  from origin capacity. Correct by construction — a cached lesson tagged with a SHA stays the right
  answer for that SHA.
- **Media** — long-TTL; moves to object storage behind the same CDN at higher stages.

**The million-user evolution**

Make content URLs SHA-addressed and the objects immutable (`max-age=1y`): the origin then serves
each lesson roughly **once per content push per region**, and reads become origin-less. Staleness
becomes a dial on the *pointer* (which SHA is current), never a gamble on the *data*.

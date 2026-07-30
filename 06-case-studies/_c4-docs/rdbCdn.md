---
title: CDN
kind: CDN
technology: CDN
---

## 🌍 CDN

The **CDN** is the download path's last rung: blob storage lives in a region, users don't, so frequently fetched files are served from an edge node near the requester. Security carries over from the presigned pattern — **signed CDN URLs** with a short (~5 minute) expiry, validated at the edge, so a leaked link self-expires and permission checks still happen server-side before any URL is minted.

**Responsibilities**

- Serve **hot** file downloads from edge caches; fill from blob storage on miss.
- Validate URL signatures and expiry at the edge — no round trip to the File Service per download.
- Cache *strategically*: CDNs bill for what they cache, so cache-control headers and invalidation keep only genuinely hot content at the edge, not every byte ever uploaded.

The instructive part of this container is that it almost didn't make the cut — and in the sibling WhatsApp design, it *didn't*. A chat attachment has at most 100 recipients, so edge caching buys nothing there; a widely shared file here may be downloaded by thousands. Same pattern, opposite verdict, and the deciding variable is **read fan-out per object**. Saying that sentence in an interview is worth more than drawing the box: a CDN is not a default garnish, it's a bet that many readers will want the same bytes from many places.

**Where it breaks.** On the wallet before anything technical: caching cold personal files at the edge is pure cost, since most files in a storage product are write-once, read-maybe-once, by one person. Signed-URL expiry adds a second sharp edge — a long download begun near the expiry boundary must complete on the established connection or fail, so lifetime tuning is a real operational knob, not a footnote.

---
title: Click ingest
kind: Service
technology: Python · FastAPI
---

## ⚙️ Click ingest

**Click ingest** is the door, and the design's key insight is how much correctness work belongs *at* the door rather than deeper in the pipeline. A windowed stream operator can only dedup within its window — the same impression clicked at 12:00:59 and again at 12:01:01 lands in two different windows and counts twice. So dedup lives here, before the stream: verify the impression ID's **signature** first (an unsigned unique ID invites fraud — a script minting fresh *"unique"* IDs that all get counted), then check the ID against a Redis set; seen means drop, new means record and append. This is the end-to-end argument in ad-tech clothes: only an identifier minted at the true source — the ad *impression* — and carried through the whole path can suppress duplicates the frameworks below can't see, like a browser retrying a POST whose 302 got lost.

**Responsibilities**

- `POST /click`: verify signature → dedup check → append to the click log → **302 redirect** to the advertiser. Server-side redirect, so every click passes through us; record, then redirect.
- Stay **stateless** — signature needs only the secret key, dedup state lives in Redis — so the fleet scales horizontally behind a load balancer to absorb the 10k/s peak.
- Stamp the event's **event time** at receipt (a trustworthy server clock), the timestamp every window downstream will bucket by.

**Where it breaks.** The dedup cache is the soft spot: ~1.6 GB for a day of impression IDs is tiny, but losing it reopens the double-count window — hence a replicated Redis Cluster with persistence, for a cache whose contents you can't recompute.

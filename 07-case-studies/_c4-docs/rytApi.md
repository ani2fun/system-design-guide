---
title: Upload & metadata API
kind: Service
technology: Python · FastAPI
---

## ⚙️ Upload & metadata API

The **Upload & metadata API** is the container defined by what it *doesn't* do: video bytes never pass through it, in either direction. A tens-of-GB upload routed through app servers would put compute in the byte path — the exact mistake the Dropbox case study spent a lesson dismantling — so this API deals only in **credentials and facts**. On upload it mints resumable presigned URLs against the raw store; on watch it returns VideoMetadata, whose one load-bearing field is the primary-manifest URL the player takes to the CDN.

**Responsibilities**

- `POST /videos/presigned-url` — register the video (row created, status `uploading`), return per-chunk presigned PUTs; resume by returning only the chunks storage hasn't confirmed.
- `GET /videos/{videoId}` — return the metadata record, including the manifest URL once the pipeline has flipped the video live.
- Own the video state machine rows in the metadata DB; never own a byte of video.

The payoff is scale-shaped: this container is stateless, so it scales horizontally without ceremony — and it can afford to, because it sees roughly **one metadata request per watch session**. The tonnage — manifests, segments, every quality of every video — lands on the CDN and never touches it.

**Where it breaks.** On scope creep: any design that lets this API proxy uploads *"for validation"* or pick renditions *"for the client"* has re-inserted compute into the byte path and broken CDN cacheability. Its discipline — credentials out, facts out, bytes never — is the whole design's discipline.

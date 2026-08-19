---
title: Raw upload store
kind: Object storage
technology: S3-style object store
---

## 🪣 Raw upload store

The **Raw upload store** holds the original files exactly as uploaded — and that's *all* it holds. Its objects are the pipeline's input, never the viewer's download: after processing completes, the original is never served again. Uploaders write to it **directly**, over presigned chunked PUTs minted by the API, because a tens-of-GB file has no business traversing an app server that adds nothing to the transfer.

**Responsibilities**

- Accept fingerprinted 5–10 MB chunks over presigned PUTs, direct from the client.
- Act as the **witness** for upload progress: storage event notifications — not client claims — mark chunks uploaded, which is what makes resume trustworthy.
- Emit the `upload complete` event that kicks the transcode queue — the boundary where the synchronous upload world hands off to the asynchronous processing world.
- Retain originals after processing, as the pipeline's re-input.

That retention is the quiet strategic decision. Because the original survives, every rendition downstream is **derived data** — regenerable at any time. When a better codec arrives or a transcoder bug is found, the fix is a re-encode campaign: re-run the pipeline over the back catalog as a batch job. No original, no campaign; you'd be doing surgery on damaged state instead.

**Where it grows.** Write-mostly and cold: it absorbs the upload firehose (~1M videos/day at up to tens of GBs each) and is thereafter read only by transcode workers. Capacity is the easy dimension — object stores are built for exactly this shape.

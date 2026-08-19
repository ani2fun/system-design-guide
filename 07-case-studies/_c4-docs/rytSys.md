---
title: YouTube
kind: System
technology: Upload → process → serve · CDN-fronted
---

## 🏢 YouTube

**YouTube** is a video platform whose defining property is that *the thing you store is not the thing you serve*. It receives **one** original file and serves **hundreds** of derived files — segments, renditions, manifests — manufactured by a transcoding pipeline that sits between upload and playback and is by far the most computationally expensive thing in the design. Upload, process, serve: three stages, three scales, three bottlenecks.

**Responsibilities**

- Ingest tens-of-GB originals resumably, with bytes flowing **direct to blob storage** over presigned URLs — the API tier coordinates and exits the byte path.
- Manufacture the derived catalog: split each original into few-seconds segments, transcode each across a (resolution × codec) ladder in a parallel DAG, and assemble adaptive manifests when every piece lands.
- Serve watches from the **CDN**, not the origin — manifests and segments cached at the edge, quality chosen by the player.

The decisive fact is the read:write asymmetry: 100M watches against 1M uploads per day is 100:1 on whole videos, and orders of magnitude worse byte-for-byte, since one watch streams hundreds of segment files. Whatever else is true, the watch path must be absorbed by infrastructure that never touches this system's compute.

**Where it grows.** Each plane on its own terms: ingest rides blob-storage capacity, the pipeline scales elastically on queue depth (and runs happily on preemptible instances, because its tasks are safely re-runnable), and the watch path grows with CDN edge capacity — the origin sees roughly one metadata request per watch session.

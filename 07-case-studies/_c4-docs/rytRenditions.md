---
title: Rendition store
kind: Object storage
technology: S3-style object store
---

## 🪣 Rendition store

The **Rendition store** holds the product: every transcoded segment of every video at every (resolution × codec) rung of the ladder, plus the manifests that index them. It is the **CDN's origin** — the only consumer of these objects at watch time is an edge node filling a cache miss.

**Responsibilities**

- Store transcoded segments keyed **content-addressed**: each object's key is a pure function of its inputs — (video, segment, rendition), or a hash of the source segment plus the transcode recipe.
- Store the manifests the assembler writes: per-rendition media manifests listing segment URLs in playback order, and the primary manifest listing the renditions.
- Serve CDN fills on miss; serve the cold long tail nothing bothers to cache.

Content addressing is what makes the whole pipeline's fault-tolerance story work. A retried transcode task regenerates a **byte-identical artifact at the same key**, so re-execution is a safe overwrite or no-op — the orchestrator's bookkeeping only needs at-least-once accuracy, because this store converges regardless. And byte-stable keys mean re-processed segments don't churn the manifests that reference them.

Everything here is **derived data**: regenerable from the raw store at any time, which is why a corrupted or buggy rendition is fixed by re-running a task, never by repair.

**Where it grows.** The multiplier is per codec family, not per resolution: a full H.264 ladder costs roughly 2× its own top rendition (bitrates halve down the ladder), but adding VP9/AV1 roughly doubles stored bytes again — *"just add AV1"* is a storage and re-encode-campaign decision, not a config change.

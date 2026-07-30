---
title: Video metadata DB
kind: Relational database
technology: PostgreSQL
---

## 🗄️ Video metadata DB

The **Video metadata DB** holds the facts *about* videos while the object stores hold the bytes: uploader, title, the upload-chunk manifest while ingest is in flight, the rendition inventory once processing lands, and — above all — the video **state machine**: `uploading → processing → live`. That last field is the design's visibility switch: a video exists to viewers exactly when this row says so, and only the pipeline's fan-in step is allowed to flip it.

**Responsibilities**

- Own the state machine and the timestamped edges between its states — storage events flip `uploading → processing`; the manifest assembler flips `processing → live`.
- Serve the watch path's single origin-side read: point lookup by `videoId`, returning metadata plus the primary-manifest URL.
- Track the rendition inventory the assembler records.

The access pattern is kind: ~1M uploads/day is ~365M rows/year, every query is a point lookup by `videoId`, and nothing spans videos — so the data partitions horizontally on `videoId` with no relational tension (the POC-scale model runs a single PostgreSQL; the lesson's scaling pass reasons toward a partitioned store for exactly this shape).

**Where it breaks.** The **hot row**. Partitioning by `videoId` spreads load uniformly right up until one video goes viral and its row hammers a single partition. The mitigations are read-path classics: replicate the hot range wider and put a distributed LRU metadata cache in front — metadata is kilobytes, so caching it is cheap and nearly always right, given the design already accepts availability over consistency.

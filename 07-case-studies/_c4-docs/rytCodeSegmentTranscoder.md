---
title: SegmentTranscoder
kind: Code
technology: Python
---

## 🧩 SegmentTranscoder

**SegmentTranscoder** is the unit of parallelism: `transcode(segment, rendition)` converts exactly ONE source segment into exactly ONE rung of the (resolution × codec) ladder and returns the `ChunkRef` of the written artifact. Hundreds of these run per video — the DAG's fan-out — and the class is deliberately kept this small because independence is what makes the fan-out safe: no cross-segment state, no cross-rendition state, nothing shared to repair when one dies.

**Responsibilities**

- Read one source segment from the raw store (read-only, immutable input).
- Transcode it to one target rendition.
- Write the result to the rendition store at a **content-addressed** key — a pure function of (video, segment, rendition), or of the source segment's hash plus the transcode recipe.

**The invariant it protects: content-addressed output ⇒ idempotent execution.** Run this task twice — because a retry raced a slow worker, or a preempted instance had finished writing before it died unreported — and the second run regenerates a byte-identical artifact at the same key: a harmless overwrite or no-op. That single property is what the whole pipeline's fault-tolerance leans on: the orchestrator can blindly retry, bookkeeping can be merely at-least-once, downstream manifests see byte-stable keys that never churn, and the fleet can run on cheap spot instances that get killed more often than hardware actually fails.

**Where it breaks.** Malformed input: a corrupt container or pathological codec parameters crash this class on every attempt, so the retry cap and dead-letter verdict live above it — cheap to invoke, since its partial outputs are discardable derived data. Lands in the forthcoming POC at `06-case-studies/examples/youtube/pipeline/segment_transcoder.py`.

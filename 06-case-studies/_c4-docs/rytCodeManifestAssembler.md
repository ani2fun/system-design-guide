---
title: ManifestAssembler
kind: Code
technology: Python
---

## 🧩 ManifestAssembler

**ManifestAssembler** is the fan-in. `assemble(video)` runs exactly once per video, and only when the DAG's barrier clears: every rendition of every segment confirmed present in the rendition store. It then writes the per-rendition media manifests (segment URLs in playback order), writes the primary manifest listing the renditions, records the manifest URL in VideoMetadata, and flips the video's status to **live** — the single visibility point at which the video starts existing for viewers.

**Responsibilities**

- Enforce the **barrier**: assembly's inputs are *every* segment×rendition artifact, so it must not start while any transcode task is unfinished — the workflow-scheduler rule that a consumer runs only after all its producers succeed.
- Write media manifests + primary manifest to the rendition store.
- Flip `processing → live` in the metadata DB, atomically with recording the manifest URL.

**The invariant it protects: visibility flips once, after everything, in one place.** Run the barrier sloppily — assemble after *"most"* tasks — and the manifest references segments that don't exist yet: players fetch it from the CDN, request the missing segment, and buffer or error mid-video, and the CDN may even cache the 404. A premature manifest is a *visibility* bug, not just a pipeline bug. This is the Dropbox manifest-commit discipline one stage longer: derived data becomes visible in exactly one place, only after every constituent artifact is confirmed durable — and recovery stays clean, because a missing artifact means re-running one idempotent task, never retracting anything published.

**Where it breaks.** On its own gate: the barrier is only as trustworthy as the orchestrator's completion tracking, which is why completion means *"artifact confirmed in the store,"* not *"worker said so."* Lands in the forthcoming POC at `06-case-studies/examples/youtube/pipeline/manifest_assembler.py`.

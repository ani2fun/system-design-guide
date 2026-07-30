# POC: YouTube (transcoding DAG)

A runnable implementation of the **Design YouTube** case study
(`06-case-studies/06-youtube`), focused on the transcoding pipeline: fan a video
out into a segment×rendition matrix, transcode each piece idempotently, and fan
back in to assemble adaptive manifests and flip the video to *live*.

The three classes under [`pipeline/`](pipeline/) mirror the C4 code elements 1:1:

| C4 code element | File | Role |
| --- | --- | --- |
| `DagOrchestrator` | [`pipeline/dag_orchestrator.py`](pipeline/dag_orchestrator.py) | fan-out tasks, track completeness, retry the missing at task granularity |
| `SegmentTranscoder` | [`pipeline/segment_transcoder.py`](pipeline/segment_transcoder.py) | one segment → one rendition; content-addressed ⇒ idempotent |
| `ManifestAssembler` | [`pipeline/manifest_assembler.py`](pipeline/manifest_assembler.py) | fan-in: all renditions exist → write manifests, go live |

Container: a **FastAPI** pipeline over **Redis** (content-addressed rendition
store + video state/manifests). Real transcoding shells out to ffmpeg; here a
rendition is deterministic placeholder bytes, which is all the DAG semantics need.

## Run it

```bash
./run            # build + start pipeline (8370) + Redis (8371)
./run test       # mypy --strict + smoke
./run stop
```

## What the smoke proves

- **Fan-out / fan-in** — a 3-segment × 3-rendition video expands to **9 tasks**;
  when all 9 renditions exist, 3 adaptive manifests are assembled and the video
  goes **live**.
- **Idempotency** — re-running a completed video redoes nothing (existence =
  done) and stays live.
- **Task-granular retry** — inject a single failed task and the DAG stops at
  **8/9, processing**; a re-run transcodes only the missing task (the other 8 are
  skipped) and the video goes live. A retry never redoes finished work.

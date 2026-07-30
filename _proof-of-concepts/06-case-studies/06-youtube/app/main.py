"""Composition root + HTTP adapter (FastAPI) for the transcoding pipeline.

POST /videos runs the DAG for a video; GET /videos/{id} reports state + manifests.
`fail_segment`/`fail_rendition` inject a single failed task to show retry.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass

from fastapi import FastAPI
from pydantic import BaseModel
from redis.asyncio import Redis, from_url

from app.config import REDIS_URL
from infra.redis_ import RedisMetadataStore, RedisRenditionStore
from pipeline.dag_orchestrator import DagOrchestrator
from pipeline.manifest_assembler import ManifestAssembler
from pipeline.segment_transcoder import SegmentTranscoder


@dataclass(slots=True)
class Services:
    redis: Redis
    orchestrator: DagOrchestrator
    meta: RedisMetadataStore


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    redis: Redis = from_url(REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]
    store = RedisRenditionStore(redis)
    meta = RedisMetadataStore(redis)
    orchestrator = DagOrchestrator(SegmentTranscoder(store), ManifestAssembler(meta), store, meta)
    _services = Services(redis, orchestrator, meta)
    try:
        yield
    finally:
        await redis.aclose()
        _services = None


app = FastAPI(title="YouTube POC — transcoding pipeline", lifespan=lifespan)


class VideoReq(BaseModel):
    video_id: str
    segments: int = 3
    renditions: list[str] = ["240p", "480p", "720p"]
    fail_segment: int | None = None
    fail_rendition: str | None = None


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/videos")
async def process_video(req: VideoReq) -> dict[str, object]:
    fail = (
        (req.fail_segment, req.fail_rendition)
        if req.fail_segment is not None and req.fail_rendition is not None
        else None
    )
    progress = await services().orchestrator.process(
        req.video_id, req.segments, req.renditions, fail
    )
    return asdict(progress)


@app.get("/videos/{video_id}")
async def get_video(video_id: str) -> dict[str, object]:
    svc = services()
    return {
        "video": video_id,
        "state": await svc.meta.get_state(video_id),
        "manifests": await svc.meta.manifests(video_id),
    }

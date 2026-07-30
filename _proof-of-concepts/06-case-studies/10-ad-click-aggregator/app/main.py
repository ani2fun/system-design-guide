"""Composition root + HTTP adapter (FastAPI) for the stream aggregator.

POST /clicks feeds one click through dedup → window aggregation → idempotent
sink; GET /metrics/{ad} reads the emitted window counts.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass

import asyncpg
from fastapi import FastAPI
from pydantic import BaseModel

from app.config import LATENESS_MS, PG_DSN, WINDOW_MS
from domain.idempotent_sink import IdempotentSink
from domain.impression_deduper import ImpressionDeduper
from domain.model import Click
from domain.window_aggregator import WindowAggregator
from infra.db import create_pool
from infra.postgres import PostgresAggregateSink, PostgresDedupStore


@dataclass(slots=True)
class Services:
    pool: asyncpg.Pool
    deduper: ImpressionDeduper
    aggregator: WindowAggregator
    sink: IdempotentSink
    sink_read: PostgresAggregateSink


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    pool = await create_pool(PG_DSN)
    sink_impl = PostgresAggregateSink(pool)
    _services = Services(
        pool=pool,
        deduper=ImpressionDeduper(PostgresDedupStore(pool)),
        aggregator=WindowAggregator(WINDOW_MS, LATENESS_MS),
        sink=IdempotentSink(sink_impl),
        sink_read=sink_impl,
    )
    try:
        yield
    finally:
        await pool.close()
        _services = None


app = FastAPI(title="Ad-Click Aggregator POC", lifespan=lifespan)


class ClickReq(BaseModel):
    ad_id: str
    impression_id: str
    event_time_ms: int


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/clicks")
async def ingest(req: ClickReq) -> dict[str, object]:
    svc = services()
    if await svc.deduper.is_duplicate(req.impression_id):
        return {"counted": False, "reason": "duplicate"}
    svc.aggregator.add(req.ad_id, req.event_time_ms)
    emitted = svc.aggregator.flush()
    for window in emitted:
        await svc.sink.emit(window)
    return {"counted": True, "windows_emitted": [asdict(w) for w in emitted]}


@app.get("/metrics/{ad_id}")
async def metrics(ad_id: str) -> dict[str, object]:
    windows = await services().sink_read.get(ad_id)
    return {"ad_id": ad_id, "windows": [asdict(w) for w in windows]}


@app.post("/reset")
async def reset() -> dict[str, bool]:
    svc = services()
    async with svc.pool.acquire() as con:
        await con.execute("TRUNCATE seen, aggregates")
    svc.aggregator.reset()
    return {"ok": True}

"""Composition root + HTTP adapter (FastAPI) for the URL frontier."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator, Awaitable
from dataclasses import dataclass
from typing import cast

from fastapi import FastAPI
from pydantic import BaseModel
from redis.asyncio import Redis, from_url

from app.config import DISALLOW, INTERVAL_MS, REDIS_URL
from domain.frontier_scheduler import FrontierScheduler
from domain.politeness_gate import PolitenessGate
from domain.ports import Frontier
from domain.url_deduper import UrlDeduper
from infra.redis_ import RedisFrontier, RedisHostGate, RedisSeenStore


@dataclass(slots=True)
class Services:
    redis: Redis
    frontier: Frontier
    scheduler: FrontierScheduler


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    redis: Redis = from_url(REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]
    frontier = RedisFrontier(redis)
    scheduler = FrontierScheduler(
        frontier,
        UrlDeduper(RedisSeenStore(redis)),
        PolitenessGate(RedisHostGate(redis), DISALLOW, INTERVAL_MS),
    )
    _services = Services(redis, frontier, scheduler)
    try:
        yield
    finally:
        await redis.aclose()
        _services = None


app = FastAPI(title="Web Crawler POC — URL frontier", lifespan=lifespan)


class UrlsReq(BaseModel):
    urls: list[str]


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/seed")
async def seed(req: UrlsReq) -> dict[str, int]:
    admitted = sum([1 for url in req.urls if await services().scheduler.admit(url)])
    return {"admitted": admitted, "rejected": len(req.urls) - admitted}


@app.post("/discovered")
async def discovered(req: UrlsReq) -> dict[str, int]:
    return await seed(req)


@app.get("/next")
async def next_url() -> dict[str, str | None]:
    return {"url": await services().scheduler.next()}


@app.post("/reset")
async def reset() -> dict[str, bool]:
    await services().redis.flushdb()
    return {"ok": True}


@app.get("/stats")
async def stats() -> dict[str, object]:
    svc = services()
    hosts = await svc.frontier.hosts()
    seen = await cast("Awaitable[int]", svc.redis.scard("seen"))
    return {"seen": seen, "hosts": sorted(hosts), "admitted": svc.scheduler.admitted}

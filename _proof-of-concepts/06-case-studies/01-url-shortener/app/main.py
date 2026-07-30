"""Composition root + HTTP adapter (FastAPI).

This is the only layer that knows about both the domain and the infrastructure:
it builds the concrete adapters, injects them into the domain services, and
translates domain errors into HTTP responses. The domain has no idea FastAPI,
Postgres, or Redis exist.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from redis.asyncio import Redis, from_url

from app.config import CACHE_TTL, COUNTER_START, PG_DSN, RANGE_BATCH, REDIS_URL
from domain.base62_codec import Base62Codec
from domain.errors import DuplicateCodeError, InvalidURLError
from domain.link_creator import LinkCreator
from domain.range_lease import RangeLease
from domain.redirect_handler import RedirectHandler
from infra.db import create_pool
from infra.postgres import PostgresLinkRepository, PostgresRangeAllocator
from infra.redis_ import RedisClickPublisher, RedisRedirectCache


@dataclass(slots=True)
class Services:
    pool: asyncpg.Pool
    redis: Redis
    range_lease: RangeLease
    creator: LinkCreator
    redirect: RedirectHandler


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    pool = await create_pool(PG_DSN, COUNTER_START)
    redis: Redis = from_url(REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]

    codec = Base62Codec()
    repo = PostgresLinkRepository(pool)
    range_lease = RangeLease(PostgresRangeAllocator(pool), batch=RANGE_BATCH)
    _services = Services(
        pool=pool,
        redis=redis,
        range_lease=range_lease,
        creator=LinkCreator(repo, range_lease, codec),
        redirect=RedirectHandler(
            RedisRedirectCache(redis), repo, RedisClickPublisher(redis), CACHE_TTL
        ),
    )
    try:
        yield
    finally:
        await redis.aclose()
        await pool.close()
        _services = None


app = FastAPI(title="URL Shortener POC", lifespan=lifespan)


class CreateReq(BaseModel):
    url: str
    alias: str | None = None


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.get("/stats")
async def stats() -> dict[str, object]:
    svc = services()
    total_links = await svc.pool.fetchval("SELECT count(*) FROM links")
    return {
        "total_links": total_links,
        "redirect": svc.redirect.status(),
        "range_lease": svc.range_lease.status(),
    }


@app.post("/links", status_code=201)
async def create_link(req: CreateReq) -> dict[str, str]:
    try:
        code = await services().creator.create(req.url, req.alias)
    except InvalidURLError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicateCodeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"code": code, "short_url": f"/{code}", "long_url": req.url}


@app.get("/{code}")
async def redirect(code: str) -> RedirectResponse:
    url = await services().redirect.resolve(code)
    if url is None:
        raise HTTPException(status_code=404, detail="unknown short code")
    return RedirectResponse(url, status_code=302)

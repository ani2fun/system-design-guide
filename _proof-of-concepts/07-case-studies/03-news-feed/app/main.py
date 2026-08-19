"""Composition root + HTTP adapter (FastAPI) for the News Feed API.

Builds the adapters, injects them into the read-path domain services, and
exposes the endpoints. The domain has no idea FastAPI, Postgres, or Redis exist.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass

import asyncpg
from fastapi import FastAPI
from pydantic import BaseModel
from redis.asyncio import Redis, from_url

from app.config import CELEB_THRESHOLD, GROUP, PG_DSN, REDIS_URL, STREAM
from domain.celebrity_merger import CelebrityMerger
from domain.timeline_reader import TimelineReader
from infra.db import create_pool
from infra.postgres import PostgresFeedQueries, PostgresFollowGraph, PostgresPostRepository
from infra.redis_ import RedisFanoutQueue, RedisTimelineCache


@dataclass(slots=True)
class Services:
    pool: asyncpg.Pool
    redis: Redis
    graph: PostgresFollowGraph
    posts: PostgresPostRepository
    queries: PostgresFeedQueries
    cache: RedisTimelineCache
    queue: RedisFanoutQueue
    reader: TimelineReader


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    pool = await create_pool(PG_DSN)
    redis: Redis = from_url(REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]

    posts = PostgresPostRepository(pool)
    graph = PostgresFollowGraph(pool)
    queries = PostgresFeedQueries(pool)
    cache = RedisTimelineCache(redis)
    merger = CelebrityMerger(queries, CELEB_THRESHOLD)
    _services = Services(
        pool=pool,
        redis=redis,
        graph=graph,
        posts=posts,
        queries=queries,
        cache=cache,
        queue=RedisFanoutQueue(redis, STREAM, GROUP),
        reader=TimelineReader(cache, posts, merger),
    )
    try:
        yield
    finally:
        await redis.aclose()
        await pool.close()
        _services = None


app = FastAPI(title="News Feed POC", lifespan=lifespan)


class PostReq(BaseModel):
    author_id: int
    content: str


class FollowReq(BaseModel):
    follower_id: int
    followee_id: int


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/posts", status_code=201)
async def create_post(req: PostReq) -> dict[str, int]:
    svc = services()
    post_id = await svc.posts.add(req.author_id, req.content)
    await svc.queue.publish(post_id, req.author_id)  # async boundary → worker fans out
    return {"post_id": post_id, "author_id": req.author_id}


@app.post("/follow", status_code=201)
async def follow(req: FollowReq) -> dict[str, int]:
    await services().graph.add_follow(req.follower_id, req.followee_id)
    return {"follower_id": req.follower_id, "followee_id": req.followee_id}


@app.get("/feed")
async def feed(user_id: int, limit: int = 20) -> dict[str, object]:
    return {"user_id": user_id, "posts": await services().reader.read(user_id, limit)}


@app.get("/timeline/{user_id}")
async def raw_timeline(user_id: int, limit: int = 20) -> dict[str, object]:
    ids = await services().cache.recent_ids(user_id, limit)
    return {"user_id": user_id, "materialized_ids": ids}


@app.get("/celebrities")
async def celebrities() -> dict[str, object]:
    rows = await services().queries.celebrities(CELEB_THRESHOLD)
    return {
        "threshold": CELEB_THRESHOLD,
        "celebrities": [{"author_id": a, "followers": c} for a, c in rows],
    }


@app.get("/stats")
async def stats() -> dict[str, object]:
    svc = services()
    async with svc.pool.acquire() as con:
        posts = await con.fetchval("SELECT count(*) FROM posts")
        follows = await con.fetchval("SELECT count(*) FROM follows")
    return {"posts": posts, "follows": follows, "celeb_threshold": CELEB_THRESHOLD}

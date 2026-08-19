"""Composition root + HTTP adapter (FastAPI) for the job scheduler.

Exposes the scheduler (elect → dispatch with fencing) and worker (claim →
heartbeat → complete; reclaim) primitives so the guarantees can be driven
directly.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis, from_url

from app.config import LEASE_TTL_MS, PG_DSN, REDIS_URL, VISIBILITY_MS
from domain.model import StaleEpochError
from domain.ports import Coordinator, ExecutionStore
from infra.db import create_pool
from infra.postgres import PostgresExecutionStore
from infra.redis_ import RedisCoordinator
from scheduler.dispatcher import Dispatcher
from scheduler.leader_lease import LeaderLease
from worker.execution_claimer import ExecutionClaimer
from worker.heartbeat import Heartbeat


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(slots=True)
class Services:
    pool: asyncpg.Pool
    redis: Redis
    coord: Coordinator
    store: ExecutionStore
    dispatcher: Dispatcher
    claimer: ExecutionClaimer
    heart: Heartbeat


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    pool = await create_pool(PG_DSN)
    redis: Redis = from_url(REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]
    coord = RedisCoordinator(redis)
    store = PostgresExecutionStore(pool)
    _services = Services(
        pool, redis, coord, store,
        Dispatcher(store, coord),
        ExecutionClaimer(store, VISIBILITY_MS),
        Heartbeat(store, VISIBILITY_MS),
    )
    try:
        yield
    finally:
        await redis.aclose()
        await pool.close()
        _services = None


app = FastAPI(title="Job Scheduler POC", lifespan=lifespan)


class NodeReq(BaseModel):
    node: str


class ExecReq(BaseModel):
    execution_id: str
    due_ms: int = 0


class DispatchReq(BaseModel):
    execution_id: str
    epoch: int


class WorkReq(BaseModel):
    execution_id: str
    worker: str


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/leader/acquire")
async def acquire(req: NodeReq) -> dict[str, object]:
    lease = LeaderLease(services().coord, req.node, LEASE_TTL_MS)
    is_leader = await lease.acquire()
    return {"leader": is_leader, "epoch": lease.epoch}


@app.get("/epoch")
async def epoch() -> dict[str, int]:
    return {"epoch": await services().coord.current_epoch()}


@app.post("/executions")
async def register(req: ExecReq) -> dict[str, bool]:
    await services().store.register(req.execution_id, req.due_ms)
    return {"ok": True}


@app.post("/dispatch")
async def dispatch(req: DispatchReq) -> dict[str, bool]:
    try:
        await services().dispatcher.dispatch(req.execution_id, req.epoch)
    except StaleEpochError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"dispatched": True}


@app.post("/claim")
async def claim(req: WorkReq) -> dict[str, bool]:
    return {"claimed": await services().claimer.claim(req.execution_id, req.worker, now_ms())}


@app.post("/heartbeat")
async def heartbeat(req: WorkReq) -> dict[str, bool]:
    return {"ok": await services().heart.beat(req.execution_id, req.worker, now_ms())}


@app.post("/complete")
async def complete(req: WorkReq) -> dict[str, bool]:
    return {"ok": await services().store.complete(req.execution_id, req.worker)}


@app.post("/reclaim")
async def reclaim() -> dict[str, int]:
    return {"reclaimed": await services().store.reclaim_expired(now_ms())}


@app.get("/executions/{execution_id}")
async def status(execution_id: str) -> dict[str, object]:
    return {"execution_id": execution_id, "status": await services().store.status(execution_id)}

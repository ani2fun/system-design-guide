"""Composition root + HTTP adapter (FastAPI) for the rate limiter."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import FastAPI
from pydantic import BaseModel
from redis.asyncio import Redis, from_url

from app.config import DEFAULT, REDIS_URL, RULES
from domain.atomic_counter import AtomicCounter
from domain.rule_resolver import RuleResolver
from domain.window_algorithm import WindowAlgorithm
from infra.redis_ import RedisScriptRunner


@dataclass(slots=True)
class Services:
    redis: Redis
    resolver: RuleResolver
    algo: WindowAlgorithm


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    redis: Redis = from_url(REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]
    _services = Services(
        redis,
        RuleResolver(RULES, DEFAULT),
        WindowAlgorithm(AtomicCounter(RedisScriptRunner(redis))),
    )
    try:
        yield
    finally:
        await redis.aclose()
        _services = None


app = FastAPI(title="Rate Limiter POC", lifespan=lifespan)


class AllowReq(BaseModel):
    key: str


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/allow")
async def allow(req: AllowReq) -> dict[str, object]:
    svc = services()
    rule = svc.resolver.resolve(req.key)
    decision = await svc.algo.check(req.key, rule)
    return {
        "key": req.key,
        "algorithm": rule.algorithm.value,
        "limit": rule.limit,
        "allowed": decision.allowed,
        "remaining": decision.remaining,
        "retry_after_ms": decision.retry_after_ms,
    }

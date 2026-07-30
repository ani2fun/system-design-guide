"""Composition root + HTTP adapter (FastAPI) for the Uber POC.

Combines the location write-path (driver pings → geo index) and the matching
service (nearby → lock → offer → trip) for a self-contained demo.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis, from_url

from app.config import PG_DSN, REDIS_URL
from domain.driver_lock import DriverLock
from domain.nearby_driver_query import NearbyDriverQuery
from domain.offer_flow import OfferFlow
from infra.db import create_pool
from infra.postgres import PostgresTripStore
from infra.redis_ import RedisGeoIndex, RedisLockStore


@dataclass(slots=True)
class Services:
    pool: asyncpg.Pool
    redis: Redis
    geo: RedisGeoIndex
    offers: OfferFlow


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    pool = await create_pool(PG_DSN)
    redis: Redis = from_url(REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]
    geo = RedisGeoIndex(redis)
    offers = OfferFlow(
        NearbyDriverQuery(geo), DriverLock(RedisLockStore(redis)), PostgresTripStore(pool)
    )
    _services = Services(pool, redis, geo, offers)
    try:
        yield
    finally:
        await redis.aclose()
        await pool.close()
        _services = None


app = FastAPI(title="Uber POC — matching service", lifespan=lifespan)


class Location(BaseModel):
    lon: float
    lat: float


class MatchReq(BaseModel):
    request_id: str
    lon: float
    lat: float


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/drivers/{driver_id}/location")
async def ping(driver_id: str, loc: Location) -> dict[str, bool]:
    await services().geo.add_driver(driver_id, loc.lon, loc.lat)
    return {"ok": True}


@app.post("/match")
async def match(req: MatchReq) -> dict[str, object]:
    result = await services().offers.match(req.request_id, req.lon, req.lat)
    if result is None:
        raise HTTPException(status_code=409, detail="no available driver nearby")
    return {"request_id": result.request_id, "driver_id": result.driver_id, "trip_id": result.trip_id}


@app.get("/stats")
async def stats() -> dict[str, int]:
    trips = await services().pool.fetchval("SELECT count(*) FROM trips")
    distinct_drivers = await services().pool.fetchval("SELECT count(DISTINCT driver_id) FROM trips")
    return {"trips": trips, "distinct_drivers_assigned": distinct_drivers}

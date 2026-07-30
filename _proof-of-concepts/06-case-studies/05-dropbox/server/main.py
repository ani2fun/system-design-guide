"""File service — metadata plane + content-addressed chunk store (FastAPI).

Bytes never traverse an app server in real Dropbox (presigned URLs to S3); here
the service holds the chunks directly in Postgres to keep the POC self-contained.
The important parts are faithful: content-addressed chunks (key = hash, deduped)
and an atomic manifest commit that flips a version visible.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

import asyncpg
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

from server.config import PG_DSN
from server.db import create_pool

_pool: asyncpg.Pool | None = None


def pool() -> asyncpg.Pool:
    assert _pool is not None, "pool not initialized"
    return _pool


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _pool
    _pool = await create_pool(PG_DSN)
    try:
        yield
    finally:
        await _pool.close()
        _pool = None


app = FastAPI(title="Dropbox POC — file service", lifespan=lifespan)


class ManifestReq(BaseModel):
    path: str
    hashes: list[str]


class HashesReq(BaseModel):
    hashes: list[str]


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.get("/files/manifest")
async def get_manifest(path: str) -> dict[str, list[str]]:
    row = await pool().fetchval("SELECT hashes FROM files WHERE path = $1", path)
    return {"hashes": list(row) if row is not None else []}


@app.put("/files/manifest")
async def put_manifest(body: ManifestReq) -> dict[str, bool]:
    await pool().execute(
        "INSERT INTO files (path, hashes) VALUES ($1, $2) "
        "ON CONFLICT (path) DO UPDATE SET hashes = EXCLUDED.hashes",
        body.path,
        body.hashes,
    )
    return {"ok": True}


@app.post("/chunks/missing")
async def missing(body: HashesReq) -> dict[str, list[str]]:
    present = await pool().fetch(
        "SELECT hash FROM chunks WHERE hash = ANY($1::text[])", body.hashes
    )
    present_set = {r["hash"] for r in present}
    return {"missing": [h for h in body.hashes if h not in present_set]}


@app.put("/chunks/{chunk_hash}")
async def put_chunk(chunk_hash: str, request: Request) -> dict[str, bool]:
    data = await request.body()
    await pool().execute(
        "INSERT INTO chunks (hash, data) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        chunk_hash,
        data,
    )
    return {"ok": True}


@app.get("/chunks/{chunk_hash}")
async def get_chunk(chunk_hash: str) -> Response:
    data = await pool().fetchval("SELECT data FROM chunks WHERE hash = $1", chunk_hash)
    if data is None:
        raise HTTPException(status_code=404, detail="no such chunk")
    return Response(content=bytes(data), media_type="application/octet-stream")


@app.get("/stats")
async def stats() -> dict[str, int]:
    async with pool().acquire() as con:
        chunks = await con.fetchval("SELECT count(*) FROM chunks")
        stored = await con.fetchval("SELECT coalesce(sum(length(data)), 0) FROM chunks")
        files = await con.fetchval("SELECT count(*) FROM files")
    return {"chunks": chunks, "bytes_stored": stored, "files": files}

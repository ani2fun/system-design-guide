"""Composition root + WebSocket adapter (FastAPI) for a chat server.

Terminates persistent WebSockets, wires the domain services, and runs a
background subscriber so messages published to this server's channel reach the
sockets it holds. Two instances (chat1/chat2) over one Redis demonstrate
cross-server delivery.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis, from_url

from app.config import REDIS_URL, SERVER_ID
from domain.connection_registry import ConnectionRegistry
from domain.message_router import MessageRouter
from domain.model import Kind, Message
from domain.receipt_tracker import ReceiptTracker
from infra.redis_ import RedisInboxStore, RedisMessageBus, RedisPresenceStore


@dataclass(slots=True)
class Services:
    redis: Redis
    registry: ConnectionRegistry
    router: MessageRouter
    tracker: ReceiptTracker
    bus: RedisMessageBus


_services: Services | None = None


def services() -> Services:
    assert _services is not None, "services not initialized"
    return _services


async def _subscriber(bus: RedisMessageBus, router: MessageRouter) -> None:
    async for payload in bus.listen(f"srv:{SERVER_ID}"):
        await router.deliver_local(Message.from_json(payload))


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _services
    redis: Redis = from_url(REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]
    registry = ConnectionRegistry(RedisPresenceStore(redis), SERVER_ID)
    bus = RedisMessageBus(redis)
    router = MessageRouter(registry, RedisInboxStore(redis), bus)
    tracker = ReceiptTracker(router)
    _services = Services(redis, registry, router, tracker, bus)

    subscriber = asyncio.create_task(_subscriber(bus, router))
    try:
        yield
    finally:
        subscriber.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await subscriber
        await redis.aclose()
        _services = None


app = FastAPI(title="WhatsApp POC", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, object]:
    return {"ok": True, "server": SERVER_ID}


@app.websocket("/ws")
async def ws(websocket: WebSocket, user_id: str) -> None:
    svc = services()
    await websocket.accept()

    async def send(payload: str) -> None:
        await websocket.send_text(payload)

    await svc.registry.connect(user_id, send)
    await svc.router.drain(user_id)  # deliver anything that queued while offline
    try:
        while True:
            data: dict[str, Any] = json.loads(await websocket.receive_text())
            if data.get("type") == "send":
                await svc.router.route(
                    Message(
                        id=str(data["id"]),
                        sender=user_id,
                        recipient=str(data["to"]),
                        kind=Kind.MSG,
                        text=str(data.get("text", "")),
                    )
                )
            elif data.get("type") == "read":
                await svc.tracker.on_read(user_id, str(data["to"]), str(data["id"]))
    except WebSocketDisconnect:
        pass
    finally:
        await svc.registry.disconnect(user_id)

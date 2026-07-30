"""WebSocket smoke test: cross-server delivery + offline inbox drain.

Needs the stack up (./run up). Uses the `websockets` client (ships with
uvicorn[standard]).

    python tests/smoke.py
"""

import asyncio
import json
from typing import Any

import websockets

CHAT1 = "ws://localhost:8351/ws"
CHAT2 = "ws://localhost:8352/ws"


async def recv(ws: Any, timeout: float = 5.0) -> dict[str, Any]:
    raw = await asyncio.wait_for(ws.recv(), timeout)
    parsed: dict[str, Any] = json.loads(raw)
    return parsed


async def main() -> None:
    # alice on chat1, bob on chat2 → message crosses servers via Redis pub/sub
    async with (
        websockets.connect(f"{CHAT1}?user_id=alice") as alice,
        websockets.connect(f"{CHAT2}?user_id=bob") as bob,
    ):
        await alice.send(json.dumps({"type": "send", "id": "m1", "to": "bob", "text": "hi bob"}))
        got = await recv(bob)
        assert got["id"] == "m1" and got["text"] == "hi bob" and got["kind"] == "msg", got
        print("  ok  cross-server delivery: bob (chat2) received m1 from alice (chat1)")

        receipt = await recv(alice)
        assert receipt["kind"] == "receipt" and receipt["state"] == "delivered", receipt
        assert receipt["receipt_of"] == "m1", receipt
        print("  ok  alice received the 'delivered' receipt")

    # offline: alice messages carol (offline) → queued → carol drains on connect
    async with websockets.connect(f"{CHAT1}?user_id=alice") as alice:
        await alice.send(json.dumps({"type": "send", "id": "m2", "to": "carol", "text": "you were offline"}))
        await asyncio.sleep(0.4)  # let the server write the inbox row

    async with websockets.connect(f"{CHAT2}?user_id=carol") as carol:
        got = await recv(carol)
        assert got["id"] == "m2" and got["text"] == "you were offline", got
        print("  ok  offline inbox: carol drained m2 on reconnect")

    print("PASS  whatsapp smoke")


if __name__ == "__main__":
    asyncio.run(main())

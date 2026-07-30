# POC: WhatsApp (realtime messaging)

A runnable implementation of the **Design WhatsApp** case study
(`06-case-studies/04-whatsapp`), focused on the two things that make realtime
messaging hard: **routing a message to a socket that may live on another
server**, and **not losing it when the recipient is offline**.

Two chat servers over one Redis demonstrate cross-server delivery. The three
classes mirror the C4 code-level elements 1:1:

| C4 code element | File | Role |
| --- | --- | --- |
| `ConnectionRegistry` | [`domain/connection_registry.py`](domain/connection_registry.py) | which user's socket is on which server (local map + Redis presence) |
| `MessageRouter` | [`domain/message_router.py`](domain/message_router.py) | inbox-first, then deliver: local socket, else publish to the holder |
| `ReceiptTracker` | [`domain/receipt_tracker.py`](domain/receipt_tracker.py) | sent → delivered → read; a receipt is a message going back |

Containers: two **FastAPI** WebSocket **chat servers**, a **Redis** pub/sub bus
(cross-server delivery), and a **Redis** per-user inbox (offline queue).

## Run it

```bash
./run            # build + start redis + chat1 (8351) + chat2 (8352)
./run test       # mypy --strict + WebSocket smoke
./run stop
```

## What to observe

**Cross-server delivery.** `alice` connects to **chat1**, `bob` to **chat2**.
When alice sends to bob, chat1 can't see bob's socket — it looks bob up in the
presence store, finds him on chat2, and publishes to chat2's channel; chat2's
subscriber delivers to bob's socket. alice then gets a **delivered** receipt
routed back the same way.

**Offline inbox.** Every message is written to the recipient's inbox *before*
delivery and deleted only on ack. Message `carol` while she's offline and it
waits; when she connects, the server **drains** her inbox onto the new socket.

`./run test` proves both paths end-to-end over real WebSockets.

## Notes & simplifications

- The L4 load balancer / socket pinning from the container view is stood in for
  by connecting clients directly to a chosen server; the routing logic is the
  same. Media (E2E-encrypted blobs) is out of scope.
- Delivery is at-least-once; a real client dedups by message id. Inbox ordering
  uses sorted message ids for determinism.

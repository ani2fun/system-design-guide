---
title: WhatsApp
kind: System
technology: Persistent connections · store-and-forward
---

## 🏢 WhatsApp

**WhatsApp** is a realtime messaging system: bidirectional delivery, offline inboxes, and receipts, at billions of persistent connections. Structurally it is a **store-and-forward system for payloads it has no reason to open** — every mechanism inside consumes only metadata (userIds, chatIds, message ids, sequence numbers), which is why end-to-end encryption changes almost nothing about this architecture.

**Responsibilities**

- Deliver a message to its recipient within ~500 ms when both parties are online — by *pushing* down an open socket, because polling at that grain is ruinously wasteful.
- Hold undelivered messages durably (up to 30 days) for recipients who are offline, and drain them on reconnect.
- Drive the sent → delivered → read receipt ladder, each tick pinned to a machine-checkable event.
- Move media as opaque encrypted blobs, out-of-band of the message path.

The decisive design fact: choosing WebSockets makes the connection **state**. A stateless HTTP fleet routes any request anywhere; a socket fleet cannot — the message for Bob must reach the specific machine holding Bob's socket. Everything interesting in the container view (the L4 balancer, the pub/sub bus, the Inbox) is a consequence of that one decision.

**Where it grows.** Durability and speed are bought separately: the Inbox transaction makes *"sent"* true, the lossy pub/sub hop makes delivery fast, and the client's ack-plus-dedup turns at-least-once transport into effectively-once conversation. Group fan-out stays tractable only because group size is capped at 100 — a product decision doing structural work.

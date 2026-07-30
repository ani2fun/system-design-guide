---
title: User
kind: Actor
technology: Human · WebSocket
---

## 👤 User

The **User** breaks the pattern of every previous case study: they are not a request-maker but a **conversation partner** — they receive as much as they send, and the thing they receive was never asked for. HTTP has no verb for that, which is why this actor connects over a persistent WebSocket instead of firing stateless requests.

**Responsibilities**

- Hold one long-lived `wss://` connection per *device* — one user may be a phone, a tablet, and a laptop, each with its own socket and its own delivery state.
- Send messages with a **client-generated message id**, so a retry after a timeout is recognized as a duplicate, not a second message.
- **Ack every push** at the application level — the ack, not the TCP write, is what *"delivered"* means — and dedup redelivered ids on receipt.
- Upload and download media directly against blob storage via presigned URLs; the chat servers never touch the bytes.

The defining property of this actor: **they may be offline for days.** The whole Inbox tier exists because a message sent to a powered-off phone must survive until that phone returns.

**Where it breaks.** Users are the reason delivery is at-least-once rather than exactly-once at the transport: their networks die mid-ack, their apps crash after receiving, their clocks can't be trusted for ordering. The design answers each at the edge — idempotent receive, Inbox redelivery, server-assigned sequence numbers — rather than pretending the actor is reliable.

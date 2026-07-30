---
title: MessageRouter
kind: Code
technology: Python
---

## 🧩 MessageRouter

**MessageRouter** owns `route(msg)` — the decision at the heart of the chat server. Three paths, tried in order of cheapness:

**Responsibilities**

- **Local:** ask `ConnectionRegistry.locate()` — if the recipient's socket is on *this* server, push `newMessage` straight down it.
- **Remote:** otherwise publish to the recipient's channel; whichever chat server holds the socket is subscribed and delivers.
- **Nobody:** when no server holds a socket, the message rests in the recipient's Inbox row — already committed before any delivery was attempted — and waits for reconnect.

**The invariant it maintains:** delivery is **at-least-once, never at-most-once.** The router may push a message twice (a crash between the push and the Inbox delete forces a replay — a missing ack *must* trigger redelivery, or crashes lose messages), but it may never silently drop one, because the durable Inbox write precedes every delivery attempt. The duplicate dies at the client: every message carries a unique id, and a redelivered id is acked but not rendered. At-least-once transport plus that idempotent receive composes into what the lesson calls **effectively-once** — the *effect* lands once even when processing repeats. The router does not try to be smarter than that; exactly-once transport is not on the menu.

**Where it breaks.** Group fan-out multiplies it: one message to a 100-person group is up to ~99 publishes and ~300 Inbox rows, all downstream of one `route()` call — the product's group-size cap is what keeps this loop bounded. Lands in the forthcoming POC at `06-case-studies/examples/whatsapp/app/message_router.py`.

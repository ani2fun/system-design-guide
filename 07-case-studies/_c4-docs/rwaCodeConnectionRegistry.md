---
title: ConnectionRegistry
kind: Code
technology: Python
---

## 🧩 ConnectionRegistry

**ConnectionRegistry** is the routing table: which user's socket lives on which chat server *right now*. It is the in-memory `userId → connection` map every chat server keeps for its own sockets, paired with the subscription side-effect that makes cross-server lookup work — registering a user here is also what subscribes this server to that user's pub/sub topic.

**Responsibilities**

- `register(user_id, socket)`: record the mapping when a connection lands, and subscribe to the user's channel so remote publishes reach this server.
- `unregister(user_id)`: drop the mapping and the subscription on disconnect.
- `locate(user_id)`: the lookup **every delivery starts with** — return the local socket if this server holds the recipient, or nothing, telling the router to go remote.

**The invariant it maintains:** the registry is consulted before every delivery, and its state is updated purely as a side effect of connect/disconnect — nobody ever computes or assigns placement. That is rung 4 of the lesson's routing ladder: the subscription *is* the registry, which is why scaling the fleet is not a re-hashing event.

**Where it breaks.** The map is deliberately volatile — a server crash forgets every socket it held, and that's safe only because durability lives in the Inbox, not here. The hazard is the gap: between a disconnect and the reconnect's `register`, publishes to that user hit no subscriber and vanish from the pub/sub layer, caught later by the Inbox drain. Lands in the forthcoming POC at `06-case-studies/examples/whatsapp/app/connection_registry.py`.

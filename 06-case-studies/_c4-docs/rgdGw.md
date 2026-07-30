---
title: Connection gateway
kind: API gateway
technology: WebSocket gateway
---

## 🚪 Connection gateway

The **Connection gateway** answers the routing question this architecture lives or dies on: which server does an editor's socket land on? Not *"any healthy one"* — a plain load balancer is exactly wrong here. OT requires all ops for a document to pass through **one transform-and-sequence point**, so every editor of document X must reach the *same* Document server. The gateway routes by **consistent hash of the document id**: `hash(docId)` names the single owner, and the connection lands there.

**Responsibilities**

- Accept an editor's initial HTTP connect naming the document, resolve the ring owner of `hash(docId)`, and steer the connection to it (in the lesson's mechanics, a non-owner redirects the client to the owner, which then upgrades to a WebSocket).
- Track ring membership (the lesson keeps it in ZooKeeper) so routing follows server joins, leaves, and failures.
- Stay out of the data path once the socket is pinned — ops, acks, and cursors flow editor-to-owner.

Contrast with WhatsApp's gateway, which only needed *delivery* and could use sloppy pub/sub routing: here the requirement is **ordering authority**, so deterministic placement is non-negotiable.

**Where it breaks.** Ring changes. Adding or removing a Document server is a state-migration event: displaced documents' connections drop and re-dial against the new owner, and both rings may see traffic mid-transition. A crash is the same event without the scheduling — which is why clients carry `baseRev` and buffered ops, turning reconnection into a resync rather than a data-loss window.

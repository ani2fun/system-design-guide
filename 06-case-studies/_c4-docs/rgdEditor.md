---
title: Editor
kind: Actor
technology: Human · browser tab · WebSocket
---

## 👤 Editor

The **Editor** is one of up to ~100 people typing in the same document at the same time — and their browser tab is not a thin client. It holds a **local replica** of the document and applies every keystroke immediately (local echo inside a 16 ms frame budget), *before* the server confirms anything. That makes the tab a participant in the convergence algorithm, not just a display: it runs client-side OT too.

**Responsibilities**

- Apply each keystroke locally, instantly, then send `OP {docId, baseRev, op}` up the WebSocket — `baseRev` declares which document state the edit was authored against.
- Transform incoming broadcast ops against its own not-yet-acked local ops before applying them — server and client see different arrival orders of the same ops; OT guarantees both converge.
- On reconnect (server crash, ring change), re-run the connect-redirect dance and resync from the last acked revision, replaying buffered unacked ops.
- Send cursor positions as ephemeral presence messages — never expecting them to be stored.

The load-bearing habit is honesty about context: every op the editor sends says what it was looking at when it typed. Without `baseRev`, the server could not tell sequential edits from concurrent ones.

**Where it breaks.** Long offline periods: an editor returning after an hour carries a queue of ops authored against an ancient revision — transformable in principle, but OT's correctness burden grows ugly with divergence. This design treats offline as short-lived disconnection; true offline-first is CRDT territory.

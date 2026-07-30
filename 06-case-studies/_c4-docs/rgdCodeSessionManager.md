---
title: SessionManager
kind: Code
technology: Python
---

## 🧩 SessionManager

**SessionManager** owns who is in this document *right now*: `join(user, socket)`, `leave(user)`, and `broadcast(op)` — the fan-out that delivers each transformed op to every other connected editor. Because consistent hashing pins all editors of a document to this one server, the broadcast is a for-loop over local sockets — at most ~100 iterations, never a distributed system.

**Responsibilities**

- Maintain the per-document in-memory session map: connected editors and their sockets.
- Broadcast each transformed op from `OtEngine` to everyone but its author.
- Handle presence: relay cursor-position deltas over the same sockets, seed a new joiner with the current cursor map from memory, broadcast removal on hangup.

**The invariant it maintains:** presence is **ephemeral — it dies with the session and is never logged.** A cursor position is meaningful only while its socket lives, so it gets no database row anywhere: the connection *is* the registry. This is a deliberate asymmetry with ops — an op missing from the log is a lost keystroke, while a cursor missing from memory is a blink that self-heals on the next move. Persisting presence would buy a write path at cursor-move frequency for data nobody wants historically.

**Where it breaks.** Server handoff: on a crash or ring change, the session map vanishes with the process — editors see cursors blink out, reconnect to the new owner, and presence rebuilds from live sockets. Cursor traffic is also the chattiest, least important message type, so clients batch and debounce it. Lands in the forthcoming POC at `06-case-studies/examples/google-docs/app/session_manager.py`.

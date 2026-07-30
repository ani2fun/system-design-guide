---
title: Google Docs
kind: System
technology: Operational Transformation · event-sourced op log
---

## 🏢 Google Docs

**Google Docs** is a collaborative editing system, and its hard problem is not scale — it is the **data type**. In a document every keystroke is a write, and users notice every loss; last-write-wins, which silently discards one of two concurrent writes, is disqualified on contact. The system's contract is strong eventual consistency: any two replicas that have seen the same set of operations are in the same state, with no keystroke lost.

**Responsibilities**

- Converge concurrent edits via **Operational Transformation**: the server rewrites each incoming op against the concurrent ops it hadn't seen, so every replica applies the same effect in the same order.
- Route every editor of document X to the **same document server** — OT needs one canonical op order, so one process per document is the ordering authority.
- Persist **operations, not text**: the document is a fold over an append-only op log; the readable text is derived, recomputable state.
- Keep cold loads fast by periodically folding the log into snapshots — and get version history nearly free by retaining the superseded ones.
- Broadcast presence (cursors, membership) over the same sockets, entirely in memory — ephemeral data that dies with the connection.

**Where it grows.** Scale lives in *document count* (billions), not per-document load: the ≤100-editor cap bounds each session, so fleet sizing follows connections. The celebrity problem is the hot document — mitigated by the cap itself, with overflow arrivals downgraded to readers.

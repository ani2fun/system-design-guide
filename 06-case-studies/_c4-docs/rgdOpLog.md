---
title: Operation log
kind: Log store
technology: Log store (Cassandra, partitioned by documentId)
---

## 📜 Operation log

The **Operation log** is the system of record — and what it records is the design's defining decision. It never stores *"the text"* as its primary record; it stores the **operations**, append-only, partitioned by `documentId` and ordered within the partition. The document is a **fold over this log**: `state = fold(ops)`. This is event sourcing wearing an editor costume — the write path is a cheap sequential append that absorbs keystroke bursts (a pattern an LSM engine loves), the readable text is derived, recomputable state, and version history is a byproduct rather than a feature bolted on.

**Responsibilities**

- Accept the canonical, already-transformed op sequence from the Document server — the OT sequencer's order *is* the log order; every consumer replaying it in that order reaches the same state.
- Back the ack: the server confirms an editor's op only after the durable append, so *"acked"* means *"in the log."*
- Serve cold loads and owner handoffs: a new ring owner reloads a document by replaying its partition (from the latest snapshot forward).

**Where it grows.** Without bound — that is the curse in the envelope. An hour of fluent typing appends roughly 1–2 MB of ops for perhaps 20 KB of final text; a living document touched daily for 4 months carries hundreds of thousands of ops, and a cold open must fold every one before rendering character one. Snapshots and compaction (the Snapshot store's job) are the fix; the log's own job is only to never lose an accepted op.

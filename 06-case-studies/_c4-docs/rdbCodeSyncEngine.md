---
title: SyncEngine
kind: Code
technology: Python
---

## 🧩 SyncEngine

**SyncEngine** is the agent's state machine — the class that turns *"the watcher saw a change"* into *"every device converges."* `sync(path)` drives the pipeline: ask the Chunker for chunks and hashes, ask the ManifestDiffer what moved, upload the missing chunks, then ask the File Service to **commit the manifest** — the metadata transaction that flips the new version visible, atomically, everywhere at once.

**Responsibilities**

- Orchestrate `chunk + hash → diff → upload missing → commit` for local changes, and the mirror (`diff → download missing → apply`) for remote change events.
- Queue work while offline and replay it on reconnect — the DDIA sync-engine loop: capture, queue, ship, merge.
- `resolve_conflict(local, remote)`: on concurrent edits — causal concurrency, each side edited in ignorance of the other — **keep both copies**, materializing the loser as a conflicted copy beside the winner. Never a silent overwrite.

**The invariant it protects: upload → commit → atomic visibility flip, in that order.** Durability strictly precedes visibility: the commit fires only after every chunk is storage-confirmed, so no other device is ever told to fetch bytes that don't exist. Until the flip, a crashed or abandoned sync leaves only invisible orphaned chunks — never a half-file anyone can download. The flip is the version's linearization point; everything before it may fail, repeat, or arrive out of order, and the engine is built to retry all of it (chunk PUTs are idempotent by content address).

**Where it breaks.** At the conflict policy's edges: keep-both trades silent loss for visible clutter, and users editing on two devices mint conflicted copies faster than they merge them — the right trade for user files, but a real UX bill. Implemented in the forthcoming POC at `06-case-studies/examples/dropbox/agent/sync_engine.py`.

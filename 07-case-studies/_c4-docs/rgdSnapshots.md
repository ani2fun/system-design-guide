---
title: Snapshot store
kind: Object storage
technology: Object store
---

## 🪣 Snapshot store

The **Snapshot store** holds the periodic fold checkpoints that keep `state = fold(ops)` affordable. Event sourcing's gift is that the log is the document's complete biography; its curse is that the log only grows — and without checkpoints, a cold open of a two-year-old document would replay years of keystrokes before rendering character one. A snapshot collapses a log prefix into a single equivalent state (in the limit, one big `INSERT`), so a **cold load is the latest snapshot plus a short op tail**, not the complete works.

**Responsibilities**

- Store each fold result under a new `documentVersionId` — snapshots are immutable, written whole, read whole: object-store shaped data.
- Make compaction safe for live documents: a new snapshot is written *beside* the old one, and the metadata DB's version pointer is **flipped** as the single atomic act — no in-place mutation to race a live session.
- Turn version history into a retention policy: keep superseded versionIds instead of garbage-collecting them, and each becomes a named restore point; *"restore"* is a flip plus a new op on top.

**Where it grows / breaks.** Compaction lag is the operational metric: every overdue document is a slow cold-load and a fat memory resident on its Document server waiting to happen. And the cadence is a real trade-off — aggressive compaction gives fast loads but destroys keystroke-level history unless versions are deliberately retained; lazy compaction keeps everything and pays for it on every cold open.

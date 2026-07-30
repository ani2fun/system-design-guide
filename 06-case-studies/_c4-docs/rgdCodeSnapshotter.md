---
title: Snapshotter
kind: Code
technology: Python
---

## 🧩 Snapshotter

**Snapshotter** owns `fold(doc_id) Snapshot` — the compaction step that keeps `state = fold(ops)` from meaning *"replay 4 months of keystrokes."* It reads the canonical sequence `OtEngine` has accepted, folds a log prefix into a single equivalent state, writes it to the snapshot store under a new `documentVersionId`, and flips the pointer in the metadata DB.

**Responsibilities**

- Fold: replay the op log (from the previous snapshot forward) into one collapsed state — in the limit, one big `INSERT`.
- Write the result immutably under a fresh versionId, then flip the metadata pointer as the single atomic act — never mutate a snapshot in place.
- Run at low priority, on cadence or when the last client disconnects — the server already holds the ops in memory and nobody is editing, so the fold is cheap and race-free.

**The invariant it maintains:** a **cold load is snapshot + log tail** — snapshot-then-flip is invisible to correctness (folding a prefix then the suffix equals folding the whole log), and **compaction bounds replay**: the op tail behind the latest snapshot stays short, so cold-open cost and resident memory stay bounded no matter how old the document is.

**Where it breaks.** Cadence is the trade-off: aggressive compaction destroys keystroke-level history unless superseded versionIds are deliberately retained (retain them and version history falls out free — each is a named restore point); lazy compaction preserves everything and pays on every cold open. Compaction lag is the metric to watch — every overdue document is a slow load waiting to happen. Lands in the forthcoming POC at `06-case-studies/examples/google-docs/app/snapshotter.py`.

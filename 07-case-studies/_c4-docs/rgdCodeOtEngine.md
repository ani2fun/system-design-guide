---
title: OtEngine
kind: Code
technology: Python
---

## 🧩 OtEngine

**OtEngine** owns `apply(op, context) Op` — the transform step that makes concurrent editing converge. Each incoming op declares its `baseRev`: the revision it was authored against. Authored against the head? Sequential — apply as-is. Authored against an older revision? Concurrent — rewrite its indices against every op accepted since, then apply, assign the next revision, and hand the transformed op to `SessionManager` for broadcast.

**Responsibilities**

- Classify each op sequential vs concurrent by comparing `baseRev` to the head revision.
- Transform concurrent ops — case analysis over insert/delete pairs, shifting positions by what concurrent ops inserted or removed before them.
- Assign revisions and append the canonical op to the log; the engine's accepted order *is* the document's one true sequence.

**The invariant it maintains:** every replica applies the **same effect in the same order** — any two replicas that have seen the same ops are in the same state, no keystroke lost. Without transformation, the invariant fails visibly: the lesson's example has `Hello!`, user A inserts `, world` at 5 while B concurrently deletes position 6 (the `!`). Applied verbatim, B's delete lands on the comma — `Hello world!`, B's intent destroyed. Transformed to `DELETE(13)`, it lands on the `!` B meant: `Hello, world`, both edits preserved.

**Where it breaks.** The case analysis is notoriously easy to get wrong, and the central sequencer is OT's scaling ceiling — one process per document, which the ≤100-editor cap keeps comfortable. Lands in the forthcoming POC at `06-case-studies/examples/google-docs/app/ot_engine.py`.

# POC: Google Docs (Operational Transformation)

A runnable implementation of the **Design Google Docs** case study
(`06-case-studies/11-google-docs`), focused on the hard part: the *data type*.
Concurrent edits must converge without losing anyone's keystrokes — that's
Operational Transformation. Pure Python (OT is a pure algorithm; no Docker
adds anything to understanding it).

The three classes under [`domain/`](domain/) mirror the C4 code elements 1:1:

| C4 code element | File | Role |
| --- | --- | --- |
| `OtEngine` | [`domain/ot_engine.py`](domain/ot_engine.py) | transform an op against concurrent ops; apply to text |
| `SessionManager` | [`domain/session_manager.py`](domain/session_manager.py) | ephemeral membership + cursors |
| `Snapshotter` | [`domain/snapshotter.py`](domain/snapshotter.py) | fold the op log into a checkpoint |

`DocumentServer` ties them together as the ordering authority for a document.

## Run it

```bash
./run            # the convergence + snapshot demonstration
./run test       # mypy --strict + OT tests + demo
```

## What it shows

- **Concurrent inserts converge** — two editors inserting at position 0 from the
  same version both survive, in one agreed order (`"" → "AB"`), because the
  second op is *transformed* against the first.
- **Concurrent delete of the same char** — two deletes of the same position don't
  double-delete or crash; the second transforms to a **noop**.
- **Snapshot** — folding the op log to `state = fold(ops)` lets a cold load start
  from the latest checkpoint instead of replaying op #1; a base version older
  than the snapshot is rejected (the client must reload).

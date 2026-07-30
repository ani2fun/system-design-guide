# POC: Dropbox (content-addressed sync)

A runnable implementation of the **Design Dropbox** case study
(`06-case-studies/05-dropbox`), focused on the idea that makes file sync
tractable: **content-addressed chunks** (a chunk's name is the hash of its
bytes), from which **dedup** and **delta sync** fall out for free.

The three classes under [`agent/`](agent/) mirror the C4 code-level elements of
the sync agent 1:1:

| C4 code element | File | Role |
| --- | --- | --- |
| `Chunker` | [`agent/chunker.py`](agent/chunker.py) | split a file into chunks, name each by its content hash |
| `ManifestDiffer` | [`agent/manifest_differ.py`](agent/manifest_differ.py) | which chunks changed vs the last version? |
| `SyncEngine` | [`agent/sync_engine.py`](agent/sync_engine.py) | upload the missing chunks → commit the manifest (version visible) |

The agent talks to a **file service** ([`server/`](server/), FastAPI + Postgres)
through the `FileService` port; the HTTP adapter is [`client/`](client/). The
service is a content-addressed chunk store + a manifest table.

## Run it

```bash
./run            # build + start the file service (8360) + Postgres (8361)
./run test       # mypy --strict + pure agent unit tests + HTTP two-device sync
./run stop
```

## What the sync smoke proves

- **Device A pushes** a file → chunks uploaded, manifest committed.
- **Device B pulls** → reconstructs the identical bytes from the chunk store.
- **Delta sync** — editing only the tail of the file re-uploads **only the
  changed chunk(s)**, not the whole file (`ManifestDiffer` + `missing_chunks`).
- **Global dedup** — pushing the same content at a new path uploads **zero**
  chunks: they're already there, addressed by hash.

## Design notes (SOLID / DDD)

The agent (`agent/`) is pure device logic depending only on the `FileService`
port; the network lives in `client/`, the service in `server/`. The tests
exercise the `SyncEngine` against an in-memory fake and against the real HTTP
service — same interface. All layers are `mypy --strict` clean. Real Dropbox
sends bytes to S3 via presigned URLs (never through an app server) and uses
content-defined chunking; this POC keeps chunks in Postgres and uses fixed-size
chunks for legibility.

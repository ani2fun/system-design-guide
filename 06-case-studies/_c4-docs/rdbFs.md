---
title: File service
kind: Service
technology: Python · FastAPI
---

## ⚙️ File service

The **File service** is the coordination brain that never touches a byte of file content. It sits in the control path and has deliberately exited the data path: it checks permissions, mints grants, and records facts, which is what lets it stay small, stateless, and horizontally boring while clients and blob storage carry the tonnage.

**Responsibilities**

- **Mint presigned URLs**: ask blob storage for a time-limited (~5 minute) grant authorizing exactly one operation — PUT this chunk, GET that object — after checking the metadata store that the caller may touch the file at all. Authorization stays server-side; bytes take the short path.
- **Answer the dedup question**: given a client's fingerprint list, look up the manifest and return URLs for *missing* chunks only — chunks any user ever uploaded never travel again.
- **Track manifest progress** from upload notifications — blob storage, not the client, is the witness that a chunk landed.
- **Commit the manifest**: once every chunk is storage-confirmed, flip the file's status to `uploaded` in one metadata transaction. That flip is the file's linearization point — the single instant it becomes downloadable, shareable, and sync-announced.
- Emit change events to the sync channel so other devices learn to pull.

The ordering discipline is the correctness argument: visibility flips strictly *after* durability is total. Flip early and a sync peer can be told to fetch chunks that don't exist.

**Where it breaks.** Two-system consistency is its permanent tax: blob storage and the metadata DB can each succeed while the other fails, so everything before the commit must be repeatable and invisible — orphaned durable-but-invisible chunks are the designed failure mode, cleaned by a reaper. And a lost upload notification leaves a manifest stuck at 9,999/10,000 forever unless a reconciliation sweep backstops the events.

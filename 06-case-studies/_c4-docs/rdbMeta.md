---
title: File metadata DB
kind: Relational database
technology: PostgreSQL
---

## 🗄️ File metadata DB

The **File metadata DB** is the system of record for *what exists*. Blob storage holds bytes and knows only chunk hashes; this store holds the facts that make those bytes a file: **FileMetadata** (name, size, MIME type, owner, status `uploading`/`uploaded`), the **chunk manifest** (the ordered list of chunk fingerprints with per-chunk upload status), and **SharedFiles** (userId → fileId, so *"files shared with me"* is an indexed lookup, not a scan).

**Responsibilities**

- Hold the manifest that *is* the resume state: an interrupted upload is just a manifest with some chunks marked uploaded and some not — nothing else needs saving.
- Execute the **manifest-commit transaction** — the atomic status flip that makes a version visible. This row is where *"current version of file X"* gets its single authoritative answer; every device's sync converges on it.
- Back permission checks (via SharedFiles) before any presigned URL is minted.
- Serve the change feed (`/files/changes?since=cursor`) that stale-file polling drains.

The workload is document-shaped and low-relational — SDS reaches for DynamoDB and immediately concedes PostgreSQL would do fine; nothing in the design turns on that pick, and saying so is worth more than the pick. What the design *does* turn on: this store scales with file **count**, not file **size**. A 50 GB file costs it ~10,000 manifest entries — roughly a megabyte of metadata — trivially stored, non-trivially *updated* 10,000 times as chunk confirmations stream in.

**Where it breaks.** It is the coordination point, so its write path is the ceiling on upload completion and sync fan-out — per-chunk manifest marks are the chatty part, and batching them is the first optimization. Lose a transaction's durability guarantee and the visibility flip stops meaning anything; this row's promises are the product.

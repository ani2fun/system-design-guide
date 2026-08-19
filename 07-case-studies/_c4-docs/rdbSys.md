---
title: Dropbox
kind: System
technology: Presigned direct-to-blob · content-addressed chunks
---

## 🏢 Dropbox

**Dropbox** is cloud file storage at GB scale: upload from any device, download from any device, share, and keep every device's copy in sync. Its payloads reach **50 GB** — orders of magnitude past what a request/response body was designed to carry — and that one number dictates the architecture: the system splits into a **data plane** that moves bytes and a **metadata plane** that moves *facts about* bytes, and never lets the halves blur.

**Responsibilities**

- Move file bytes **directly between clients and blob storage** over presigned URLs — the app servers coordinate (permissions, grants, manifests) and exit the data path entirely.
- Identify every 5–10 MB chunk by the **hash of its content**, so resume, cross-user dedup, and delta sync are all the same manifest lookup — one primitive, three features.
- Make a file version visible in exactly one place: the **manifest-commit transaction** in the metadata store, which flips status only after blob storage itself has confirmed every chunk.
- Converge a user's offline-capable devices — multi-leader replication in disguise — through the metadata store as the single source of truth, with conflicts kept, never silently dropped.

The decisive design fact: the metadata store is the coordination point, and blob storage only knows chunks. *"Current version of file X"* has exactly one authoritative answer — the metadata row — and everything upstream of its commit may fail, repeat, or arrive out of order.

**Where it grows.** Each plane scales on its own terms: the byte path rides blob-storage and CDN capacity, the stateless File Service scales horizontally, and the metadata DB grows with file *count*, not file *size* — a 50 GB upload costs it a ~10,000-entry manifest, not 50 GB.

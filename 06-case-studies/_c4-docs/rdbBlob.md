---
title: Blob storage
kind: Object storage
technology: S3-style object store
---

## 🪣 Blob storage

**Blob storage** holds every byte of every file — as **content-addressed chunks**, key = SHA-256 hash of the chunk's content. Devices PUT and GET here *directly* with presigned URLs; the application tier never carries, buffers, or parses file content. This container is consumed as a building block (its internals are a different interview): what it contributes is effectively unlimited capacity, redundancy that makes *"recoverable"* someone else's solved problem, and lifecycle policies for free.

**Responsibilities**

- Store and serve chunks keyed by content hash — same bytes, same key, regardless of name, owner, or device. Hash = identity is what makes dedup a lookup and re-uploading an existing chunk a harmless no-op.
- Honor presigned grants: each URL authorizes exactly one operation on exactly one object for a few minutes, so authorization decisions stay on the File Service while enforcement happens here.
- **Report completion**: fire an event notification when a chunk lands. The store, not the client, is the witness — the manifest reflects what storage actually holds.
- Fill the CDN on miss; tier long-unread chunks to cheaper storage classes.

Content addressing quietly changes ownership semantics: a chunk may be referenced by many manifests across many users (the second upload of a popular installer transfers approximately nothing), so no single file *"owns"* its bytes.

**Where it breaks.** Exactly there: deletion. Reaping an abandoned upload's chunks is only safe if no *other* manifest references them — including one that claimed the chunk via dedup a moment ago. Reference-counting chunks across manifests is the real discipline, and it is where content addressing collects its operational tax. Note also the structural conflict: client-side per-user encryption makes identical files hash differently, so end-to-end encryption and cross-user dedup are directly at odds.

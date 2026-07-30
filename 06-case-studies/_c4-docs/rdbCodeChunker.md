---
title: Chunker
kind: Code
technology: Python
---

## 🧩 Chunker

**Chunker** is where a file stops being a file. `chunk(file)` splits it into 5–10 MB slices, and `hash(chunk)` names each slice by the SHA-256 of its content — the file's own fingerprint (the hash of the whole) becomes its `fileId`. It runs on the client, and it *must*: chunking on the server means the whole file reaches the server first, which was the problem. This class is the reason a 50 GB object becomes 10,000 independently transferable, independently retryable pieces that upload in parallel — with a progress bar falling out for free.

**Responsibilities**

- Split files into 5–10 MB chunks before any byte is transferred.
- Compute the SHA-256 fingerprint of each chunk and of the whole file — the identifiers everything downstream (manifest, dedup, delta sync) keys on.
- PUT chunk bytes directly to blob storage over presigned URLs — the one class in the agent that touches the data plane.

**The invariant it protects: content addressing — hash = identity.** Same bytes, same name, regardless of filename, owner, or device; names lie, hashes don't. Everything the design gets *"for free"* is this invariant paying out: dedup (the hash already exists → don't send it), resume (re-uploading a stored chunk is a recognizable no-op), delta sync (unchanged bytes produce unchanged fingerprints).

**Where it breaks.** Fixed boundaries. *Insert* bytes near the front of a file and every subsequent boundary shifts, every downstream hash changes, and delta sync degenerates to a full re-upload — the weakness content-defined chunking (rolling hashes, the rsync lineage) exists to fix, deliberately beyond this design's scope. Implemented in the forthcoming POC at `06-case-studies/examples/dropbox/agent/chunker.py`.

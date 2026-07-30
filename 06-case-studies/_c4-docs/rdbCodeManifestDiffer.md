---
title: ManifestDiffer
kind: Code
technology: Python
---

## 🧩 ManifestDiffer

**ManifestDiffer** answers the only question a sync ever needs answered: *which chunks must move?* `diff(local, remote)` compares the local manifest — the fingerprint list the Chunker just produced — against the remote one the File Service holds, and returns the missing set. Everything the transfer layer does next is just acting on that answer.

**Responsibilities**

- Compare fingerprint lists, local vs remote, and return the chunks present on one side but not the other — for upload (what the server lacks) and for download (what this device lacks after a change event).
- Reduce three user-facing features to the same computation: a **resume** is a diff against a partially uploaded manifest; a **dedup** hit is a diff that comes back empty; a **delta sync** is a diff where only the edited chunks differ.

**The invariant it protects: only changed chunks ever travel.** No byte moves that the other side already holds. Edit one region of a 50 GB file and unchanged chunks produce unchanged fingerprints, so the diff is one chunk — 5 MB moves instead of 50 GB, a 10,000× saving from the same mechanism that made uploads resumable. The class is only possible because the Chunker's content addressing made fingerprints comparable across devices, users, and time: a diff of *names* would be meaningless; a diff of *content hashes* is the transfer plan.

**Where it breaks.** Its answer is only as fresh as the remote manifest it diffed against — a stale read can propose re-sending chunks the server already confirmed, which content addressing makes harmless (a duplicate PUT of an existing key is a no-op) but not free. And it inherits the Chunker's fixed-boundary weakness: an insertion shifts every downstream fingerprint, and the honest diff is *"almost everything moved."* Implemented in the forthcoming POC at `06-case-studies/examples/dropbox/agent/manifest_differ.py`.

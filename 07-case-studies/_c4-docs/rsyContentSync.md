---
title: Content checkout
kind: Worker
technology: git-sync sidecar
---

## 🛠️ Content checkout

A sidecar that keeps a read-only clone of the content repository next to every origin replica —
the physical form of the design's central idea: **content is derived data, a pure function of a
git SHA.**

**How publishing works**

An author pushes Markdown → the sidecar pulls → the origin re-reads the checkout's HEAD SHA on the
next request and stamps it into every content response as `contentVersion`. No image build, no
restart, no cache purge: every cache keyed on the old SHA is simply *out of date by key*, and the
edge refills against the new version within its TTL.

**Why a checkout and not a database**

Content has exactly **one writer** (git) and infinitely many readers — no multi-writer semantics,
no conflict resolution, no replication protocol. The read model is recomputed from files; the
hardest consistency question is *"may authors see their push within a minute?"* (yes — the freshness
NFR tolerates 60 s). Per-pod clones replicate trivially because they're read-only derived state.

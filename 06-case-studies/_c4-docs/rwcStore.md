---
title: Page store
kind: Object storage
technology: S3-style object store
---

## 🪣 Page store

The **Page store** is the deliverable. Everything else in the diagram is machinery; the set of extracted-text blobs living here *is* the corpus the downstream LLM training pipeline was promised. It holds both artifacts of every crawl: the **raw HTML** (written by fetchers, read back by parsers) and the **extracted text** (written by parsers, read by consumers).

**Responsibilities**

- Absorb petabyte-class volume: 10B pages × ~2 MB averages out to **~20 PB of raw HTML** — the number that rules the storage choice. That is object-store territory, not database territory — the same instinct that sent YouTube's video bytes and Dropbox's file blocks to blob storage.
- Serve as the **checkpoint between stages**: a fetcher acks its queue message only after the HTML lands here, and a parser reads from here rather than from any worker's memory — durable intermediate state is what makes each stage independently retryable.
- Store **content-addressed / keyed by normalized URL**, which makes duplicate writes idempotent: the at-least-once redelivery upstream becomes a harmless overwrite here, never a second copy.
- Keep raw HTML *after* extraction — the cheap insurance that lets the parse stage rerun with new extraction logic (alt-text, different boilerplate rules) without re-fetching a single page.

**Where it grows.** Raw HTML dominates the bill at ~20 PB; a long-lived crawler eventually faces lifecycle policy — how long raw pages stay hot before tiering to cold storage — a cost conversation, not a correctness one.

---
title: Seen stores
kind: Key-value database
technology: Redis / KV
---

## 🔑 Seen stores

The **Seen stores** are the crawl's memory — the exact-membership answer to two different questions that beginners collapse into one. **"Have we seen this URL?"** is asked by the frontier side before a discovered link may enter (via the UrlDeduper, on normalized canonical forms). **"Have we seen this content?"** is asked by the parser after a fetch, using a content hash — because the web serves the same bytes under many names, and only hashing the bytes catches mirrors and boilerplate clones. Two layers, two keys, one store family.

**Responsibilities**

- Hold the **URL-seen set**: point lookups keyed by normalized URL, sitting on the hot path of every discovered link — thousands of checks per second, each a boring indexed lookup.
- Hold the **content hashes**: one per stored page, consulted before extraction and storage.
- Stay **exact**. The seductive alternative is a Bloom filter — constant-time, a fraction of the memory — but its false positives mean genuinely new pages silently skipped: quiet data loss for a corpus builder. SDS's verdict is anti-clever: at 10B rows a modern indexed store handles this fine; probabilistic structures earn their place when *memory*, not correctness, is the binding constraint.

**Where it breaks.** On normalization bugs upstream, not on scale: if two spellings of one URL reach the check un-canonicalized, the set dutifully calls them different and the crawler does the work twice. A spiking duplicate ratio on the dashboard usually means exactly that — or a crawler trap minting infinite URLs — not a suddenly repetitive internet.

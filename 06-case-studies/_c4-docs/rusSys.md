---
title: URL Shortener
kind: System
technology: HTTPS · read-optimized web service
---

## 🏢 URL Shortener

The **URL Shortener** turns a long URL into a code like `15ftgG` and redirects anyone who opens it. The product fits in one sentence; the design is decided by two facts hiding inside it.

**Responsibilities**

- Accept a long URL (optionally a custom alias and expiration) and return a short one.
- Redirect every `GET /{code}` to the original URL in well under 100 ms, at 99.99% availability.
- Never let two long URLs share a short code — uniqueness is the hardest requirement on the board.

The first structural fact: **reads dwarf writes**. At 100M DAU the read side averages ~5,800 redirects/second (spiking far higher), while new links arrive at roughly *one per second*. So this is a read-scaling problem wearing a CRUD costume: a cache and read replicas, not shards — 1B rows is only ~500 GB, a dataset one database node holds without noticing.

The second: **uniqueness under concurrency is the only true distributed-systems problem here**. Hashing collides at scale (birthday math: ~8.8M expected collisions at 1B codes in 6 base62 characters); a counter is unique by construction but becomes a shared object every writer depends on. The design's answer is batched counter ranges — see the ID range allocator.

**Where it breaks.** The failure surface is concentrated in two places: the counter's failover (a stale counter re-issues ranges — duplicate codes, the one unforgivable event) and hot keys (one viral link lands on one cache node, because hashing spreads keys, not load).

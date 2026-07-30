---
title: Redirect cache
kind: Cache
technology: Redis
---

## ⚡ Redirect cache

The **Redirect cache** holds hot `code → long URL` entries in memory so most redirects never touch the database. It exists because of arithmetic: memory answers in ~100 ns versus ~0.1 ms for SSD, and a single cache node serves 100k+ operations/second where a database node manages tens of thousands — and this system's reads outnumber its writes by orders of magnitude.

**Responsibilities**

- Answer the hit path of `GET /{code}` from memory.
- On a miss, let the request fall through to the link store; the handler populates the entry with a TTL on the way back (cache-aside).
- Hold entries populated at *creation* time — fresh links are the likeliest clicks, and a write-time fill serves them without touching a replica (it also sidesteps the replication-lag 404 on a brand-new link).

This is a dream caching workload: a code's target never changes, so the mapping is effectively immutable and cache coherence — normally caching's hard problem — barely exists. The only invalidation events are expiration and deletion. Hit ratio reduces to cache size plus traffic skew, and skew helps: clicks concentrate on recent and popular links, so a cache holding a small fraction of 1B mappings absorbs most reads. Operationally, hit ratio is *the* dashboard metric — it moves before p99 does.

**Where it breaks.** Hot keys. Hashing across a cache cluster spreads *keys* evenly, not *load*: one viral code lives on one node, which takes all of its traffic while its neighbors idle. The value being immutable makes the fix trivially safe — replicate the hot entry across several nodes and fan reads out among them.

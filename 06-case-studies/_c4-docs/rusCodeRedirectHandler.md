---
title: RedirectHandler
kind: Code
technology: Python
---

## 🧩 RedirectHandler

**RedirectHandler** is the hot path: `GET /{code}` at ~100:1 read skew, inside a 100 ms budget, spiking toward the design's peak. Everything about the class is shaped by that budget.

**Responsibilities**

- Look the code up in the **redirect cache** first — the hit path answers from memory.
- On a miss, fall through to the **link store** (a primary-key point read), populate the cache with a TTL, and continue.
- Answer `302 Found` with the long URL — `302`, not `301`, so clicks stay observable and links stay revocable.
- Emit a click event onto the **click stream**, fire-and-forget, *after* the redirect is already decided.

Note what the class does **not** touch: the range allocator, the codec, the write path. Its only collaborators are the cache, the store, and the stream — reads need no coordination with anything, which is why redirect capacity is just *"add nodes."* The workload it serves is caching's best case: a code's target never changes, so the cache's classic coherence problem barely exists and hit ratio reduces to size plus skew.

**The invariant it protects:** the redirect never waits on anything but the lookup itself — no click write, no analytics call, no cross-node chatter sits between request and `302`.

**Where it breaks.** Cold viral links: the instant a code goes hot it isn't cached, and thousands of concurrent misses stampede the store for one row. Write-time cache population blunts the common case (links go viral young); request coalescing is the general fix. Implemented in the forthcoming POC at `06-case-studies/examples/url-shortener/app/redirect_handler.py`.

---
title: CelebrityMerger
kind: Code
technology: Python
---

## 🧩 CelebrityMerger

**CelebrityMerger** is the read-time half of the hybrid — the class that exists because one account with 100M+ followers turns push-based fan-out into ~20M timeline writes per second for a single post, and no write path survives that.

**Responsibilities**

- Identify the few celebrity accounts *this reader* follows — the accounts the fan-out workers deliberately skipped.
- Live-query their recent posts from the **post store** (a heavily cached, write-once-read-enormously lookup).
- Merge two time-sorted streams — the materialized timeline and the live celebrity posts — into one, respecting the caller's cursor as the low-water mark both inputs honor.

The merge is cheap by construction: both inputs arrive time-sorted, so this is the textbook two-pointer merge over a page's worth of entries, and its cost scales with how many celebrities the *reader* follows (a handful), not with how many followers the *celebrity* has (the number that killed the write path). That asymmetry — push for the many, pull for the huge — is the whole hybrid, and both DDIA and the interview canon land on it independently.

**The invariant it protects:** every celebrity post appears in every follower's feed **without ever riding the fan-out pipeline** — skipping at write time never means missing at read time.

**Where it grows.** The celebrity threshold is a tunable dial: raise it and reads do more merging; lower it and the write pipeline carries more load. Implemented in the forthcoming POC at `06-case-studies/examples/news-feed/app/celebrity_merger.py`.

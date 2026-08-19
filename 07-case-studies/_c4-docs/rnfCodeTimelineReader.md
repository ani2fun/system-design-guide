---
title: TimelineReader
kind: Code
technology: Python
---

## 🧩 TimelineReader

**TimelineReader** owns `GET /feed` — the read that must land in under 500 ms, 2M times a second, and it stays fast by doing almost no work: the fan-out pipeline already did it.

**Responsibilities**

- Pull the materialized id list from the **timeline cache** (`LRANGE` on the reader's key) — one lookup, not a 200-account query.
- Hand the precomputed stream to **CelebrityMerger** to fold in live posts from any celebrity accounts the reader follows.
- **Hydrate** the merged ids into content from the post store — the read-time join the design tolerates because posts are write-once, read-enormously, and hydration cost is independent of follower counts.
- Page by **cursor**: *"the next N older than T,"* with the production tie-breaker `(timestamp, postId)` since timestamps collide.

The cursor choice is load-bearing. Offsets break twice in a feed — new posts shift every position (page 2 re-serves page 1's tail), and `OFFSET 100000` materializes and discards 100k entries. A cursor names a *record*, not a position; and it composes perfectly with the hybrid read, as the low-water mark both merge inputs respect.

**The invariant it protects:** a cursor page is stable under concurrent inserts — no re-served and no skipped entries at the page boundary, because the cursor addresses a record that inserts cannot shift.

**Where it grows.** Past the ~200-entry cap the materialized feed ends; the reader falls back to the pull path, which may be slow in peace. Implemented in the forthcoming POC at `06-case-studies/examples/news-feed/app/timeline_reader.py`.

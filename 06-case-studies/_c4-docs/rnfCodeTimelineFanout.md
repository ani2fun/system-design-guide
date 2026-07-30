---
title: TimelineFanout
kind: Code
technology: Python
---

## 🧩 TimelineFanout

**TimelineFanout** does the actual multiplication: one post event in, ~200 timeline writes out — the mailbox delivery that makes every follower's feed read a single lookup.

**Responsibilities**

- `is_celebrity(author)`: the hybrid's dial — high-follower authors are **skipped** here entirely, because their posts are merged at read time by `CelebrityMerger`; a 100M-follower delivery has no sane write-path answer.
- `fan_out(post)`: read the author's follower list from the **follow graph store**, then insert the post id into each follower's capped timeline in the **timeline cache**.
- Make every insert **idempotent**: inserting the same post id into the same timeline twice converges to one entry.

Idempotency is not an optimization here — it is what makes the pipeline's delivery semantics honest. The queue upstream redelivers on crash (at-least-once, because a lost delivery to a materialized timeline is never repaired), so every insert must tolerate being replayed: same post, same follower, same final timeline. At-least-once delivery plus idempotent writes is the composition that behaves as exactly-once, which is precisely the fault-tolerance the case study demands of a worker that dies 60,000 followers into a 100,000-follower job.

**The invariant it protects:** the idempotent insert makes redelivery safe — a replayed event can never duplicate a post in anyone's feed, so retrying is always the right call.

**Where it breaks.** The follower-list read is a point-in-time snapshot: follows that change mid-fan-out land or miss arbitrarily — accepted, since the feed is best-effort derived data. Implemented in the forthcoming POC at `06-case-studies/examples/news-feed/worker/timeline_fanout.py`.

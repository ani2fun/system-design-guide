---
title: ImpressionDeduper
kind: Code
technology: Python + Redis set
---

## 🧩 ImpressionDeduper

**ImpressionDeduper** exists because every reliability mechanism in the pipeline works by retrying, and a retry is a duplicate wearing a safety vest. The browser re-sends a POST whose 302 was lost; a consumer resumes from its last committed offset and reprocesses what it had handled but not checkpointed. Dropping duplicates is data loss's opposite twin — so the design retries freely and makes the duplicates harmless *here*, keyed by the one identifier that survives the whole journey: the **signed impression ID**, minted when the ad was shown. Not the user, not the ad — the *showing*: the same user clicking the same retargeted ad twice is legitimately two counts, which is why `(user_id, ad_id)` is the classic wrong key.

**Responsibilities**

- `seen(impression_id) → bool`: check the ID against the dedup set (Redis-backed, ~1.6 GB per 100M-click day); seen means drop, new means record-and-pass in one step.
- Sit **upstream of windowing** — a windowed operator only sees duplicates within one window, and the 12:00:59 / 12:01:01 retry pair straddles a boundary and would count twice.
- Assume the signature was verified at ingress; an unsigned *"unique"* ID is fraud's front door.

**The invariant it protects:** *one impression, one count* — end to end, from the browser down, which no framework-level exactly-once can see.

**Where it breaks.** Losing the dedup set reopens the double-count window for its whole horizon — the one cache in this design whose contents can't be recomputed. Mirrored by the forthcoming POC at `06-case-studies/examples/ad-click-aggregator/app/impression_deduper.py`.

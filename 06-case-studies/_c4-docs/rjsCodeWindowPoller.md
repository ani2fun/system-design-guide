---
title: WindowPoller
kind: Code
technology: Python
---

## 🧩 WindowPoller

**WindowPoller** owns `poll(now) list~Execution~` — the read that the whole data model was shaped to make cheap. It range-reads the current hour bucket for **PENDING executions due within the next window** (five minutes in this design) and returns them for dispatch. That's it — and the brevity is the point: because the Job service materialized every occurrence into a time-bucketed Execution row at creation, the poller never touches a cron expression. The question is never *"which of all my definitions is due?"* (a scan) but *"what did we already decide should happen soon?"* (a bounded range read of one or two partitions).

**Responsibilities**

- Range-read the due window: PENDING rows in the current bucket with `planned_time ≤ now + window` — bounded work per tick, independent of total job count.
- Run only when LeaderLease says so — a poller ticking without the lease is the two-cron-boxes failure reborn.
- Compare due-ness against monitored **wall time**, but never derive its own sleep interval from wall-clock subtraction — time-of-day clocks can jump backward, so intervals ride the monotonic clock.

**The invariant it maintains:** **work per tick is bounded by the window, not by the job count** — a 5-minute window at 10k executions/second is ~3M rows per cycle, amortized into one cheap range read every five minutes instead of a 20k-row query every two seconds.

**Where it breaks.** The hot bucket: ~36M rows land in each hour partition at target scale, so the bucket key carries a small hash suffix and the poller reads the suffixes in parallel. Lands in the forthcoming POC at `06-case-studies/examples/job-scheduler/scheduler/window_poller.py`.

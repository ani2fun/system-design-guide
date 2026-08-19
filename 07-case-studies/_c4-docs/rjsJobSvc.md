---
title: Job service
kind: Service
technology: Python · FastAPI
---

## ⚙️ Job service

The **Job service** owns the write path and performs the design's founding move: it never stores *"a cron expression to be evaluated later"* as the unit of work. It validates the schedule, writes the **Job** (the definition — what the user wants, forever), and *materializes* the first **Execution** (the instance — what should happen at 10:00:00 on a given day, and whether it did) into its hour bucket. That flip — from *"which of my definitions is due?"* (a scan over all jobs) to *"what did I already decide should happen soon?"* (a range read over time) — is what makes the scheduler tick's work bounded.

**Responsibilities**

- Validate schedules (one-shot timestamp or cron, UTC only) and write Job + first Execution.
- When a recurring execution completes, compute the next occurrence from the cron expression and insert a **fresh Execution row** — the Job row never changes; every retry, status, and dedup key hangs off the per-occurrence row.
- **Fast-path imminent jobs**: anything due sooner than the next poll window skips the scheduler tick and goes straight onto the delay queue — otherwise a job created at 09:59 for 10:00 could miss its own deadline waiting for a 5-minute poll.
- Serve status reads via the `user_id` GSI, never the time-bucketed base table.

**Where it breaks.** The fast path means *two* producers write to the queue (Job service and scheduler tick), so enqueue can never be assumed unique — one more reason the worker's `execution_id`-keyed claim, not the enqueue path, is where *"once"* is enforced.

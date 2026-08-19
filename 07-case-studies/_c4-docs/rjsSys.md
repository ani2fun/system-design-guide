---
title: Distributed Job Scheduler
kind: System
technology: Time-bucketed store + coordination lease + delay queue + worker fleet
---

## 🏢 Distributed Job Scheduler

The **Distributed Job Scheduler** is cron at cluster scale: 10,000 executions/second, each fired within 2 seconds of due, never missed, never double-fired, on machines that pause, crash, and lie about the time. A single cron box fails this brief in exactly two ways — the box dies and time doesn't stop (silent misses), or you add a second box and everything runs twice — and the architecture is the systematic answer to both.

**Responsibilities**

- Store the **definition/instance split**: Jobs by `job_id`, Executions materialized into hour buckets — so *"what's due soon?"* is a range read over *time*, never a cron-expression scan over *all jobs*.
- Keep the tick **logically singular and provably so**: a linearizable lease elects one scheduler, and a monotonic fencing epoch makes the inevitable zombie leader harmless rather than merely unlikely.
- Convert *"rows due soon"* into *"messages that appear exactly on time"* through a **delay queue** — the database gives durability and cheap time-range reads; the queue gives second-level precision and worker fault tolerance. Neither can do both.
- Execute **effectively once**: at-least-once delivery everywhere, plus an idempotent, `execution_id`-keyed conditional claim at the worker — dedup at the effect, because everything upstream can and will duplicate.

**Where it breaks.** Each guarantee has a named boundary: the lease alone can't stop a GC-paused zombie (fencing does), the fence protects the *record* not the *world* (idempotent task design does), and the characteristic failure mode is silence — nothing errors when nothing runs, so schedule lag and the misfire counter are the graphs that matter.

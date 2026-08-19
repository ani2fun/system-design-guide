---
title: Transcode task queue
kind: Message queue
technology: Queue
---

## 📮 Transcode task queue

The **Transcode task queue** is the async boundary between two things that move at incompatible rhythms: uploads, which arrive in bursts on the users' schedule, and transcode capacity, which is finite and on ours. It carries the `upload complete` events that start each video's DAG and the per-segment transcode tasks the orchestrator fans out — hundreds per video across the worker fleet.

**Responsibilities**

- Absorb upload bursts so the pipeline never has to be provisioned for peak ingest.
- Deliver transcode work to whichever worker is free — the decoupling that lets the fleet be elastic (and cheaply preemptible, since tasks are safely re-runnable).
- Serve as the **autoscaling signal**: queue depth grows, fleet grows.
- Bound retries: a video that crashes its worker will crash the retry too, so attempts are capped and the job shunts to a dead-letter path — one poison file must not become a fleet-wide grinder.

Operationally, the backlog *is* the health metric — but depth alone lies. The SLO the queue silently eats is **time-to-ready** (upload complete → video watchable): a pipeline that's *"up"* but hours behind is down as far as uploaders are concerned. Watch the age of the oldest unprocessed job, not just how many there are.

**Where it breaks.** On invisibility: nothing user-facing errors when the queue backs up — videos just stay `processing` longer and longer. The failure mode isn't a page, it's a slow drift, which is exactly why the oldest-job-age metric exists.

---
title: Heartbeat
kind: Code
technology: Python
---

## 🧩 Heartbeat

**Heartbeat** owns `beat(execution_id)` — the worker's proof of life, implemented as **extending the queue's visibility timeout** while the job runs. The elegance is what it *doesn't* need: no central health checker polling thousands of workers (doesn't scale, false-positives on blips, and the monitor itself fails), no per-job database leases (~50k renewal writes/second of pure overhead at target scale, plus every clock hazard the coordination service exists to tame). The queue already tracks every outstanding delivery — so liveness is just *"keep the message hidden."*

**Responsibilities**

- On delivery, the message is invisible for a short window (~30 s); beat every ~15 s to extend it for as long as the job genuinely runs — arbitrarily long jobs, short detection.
- Stop beating — crash, GC pause, network partition, it doesn't matter which — and do *nothing else*: silence is the signal. The window lapses, the message reappears, and a healthy worker claims attempt N+1.
- Stay per-execution: the heartbeat vouches for one running job, not for the worker process, so a wedged job can't hide behind a healthy host.

**The invariant it maintains:** **stop heartbeating ⇒ redelivery** — the liveness signal that turns a dead worker into a retry, in ≤30 seconds, with zero extra infrastructure. This is also why *"size the visibility timeout to the longest job"* is wrong: a 6-hour timeout strands a minute-one crash for 6 hours; short-timeout-plus-extension detects it in seconds.

**Where it breaks.** A *paused* worker resumes and keeps working on a job already redelivered — the heartbeat can't tell it; ExecutionClaimer's fence and idempotent task design absorb the zombie. Lands in the forthcoming POC at `06-case-studies/examples/job-scheduler/worker/heartbeat.py`.

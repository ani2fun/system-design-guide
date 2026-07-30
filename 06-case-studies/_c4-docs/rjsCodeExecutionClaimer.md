---
title: ExecutionClaimer
kind: Code
technology: Python
---

## 🧩 ExecutionClaimer

**ExecutionClaimer** owns `claim(execution_id, epoch) bool` — the worker's first act on every delivery, and the single point where the system's many duplicates go to die. Every path that can duplicate — a zombie scheduler double-enqueueing, the queue redelivering after a lost ack, a retry after a crash — produces another message bearing the *same* `execution_id`. The claimer turns that shared key into a guarantee: a **conditional write** flips the Execution row PENDING → RUNNING only if it isn't already claimed at this attempt; on success the worker proceeds, on failure it silently drops the message.

**Responsibilities**

- Execute the conditional claim keyed by `execution_id` and fencing epoch — the offset-tagged-write idea from stream processing: store the processing marker *with* the effect, so a replay detects itself.
- Treat rejection as normal operation, not error: a claimed or COMPLETED row means someone else owns this occurrence; a stale epoch means the claimant is a zombie. Either way, no-op.
- Record the attempt count, so redelivery after a genuine crash claims as attempt N+1 rather than colliding with attempt N's stale RUNNING row.

**The invariant it maintains:** **conditional claim keyed by execution_id + epoch; stale or already-claimed = no-op.** This is how at-least-once delivery becomes *effectively-once execution* — an outcome assembled at the effect, not a delivery guarantee.

**Where it breaks.** The claim protects the *record*; the job's external side effects need their own idempotence (*"set counter to X,"* not *"increment"*) — you can't recount a sent email. Lands in the forthcoming POC at `06-case-studies/examples/job-scheduler/worker/execution_claimer.py`.

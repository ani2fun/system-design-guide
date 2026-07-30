---
title: Dispatcher
kind: Code
technology: Python
---

## 🧩 Dispatcher

**Dispatcher** owns `dispatch(execution, delay, epoch)` — the hand-off from the lazy layer to the precise one. For each due execution the WindowPoller returns, it enqueues the `execution_id` into the delay queue with **delay = due − now** and the current fencing epoch. The delay is the design decision: **the queue holds the countdown, not a busy-wait**. Nothing in the scheduler sleeps until 10:00:00 or polls every two seconds to see if it's time — the message itself becomes visible at the due moment, which is how a 5-minute poll cadence coexists with a 2-second precision SLA.

**Responsibilities**

- Enqueue each due execution with its per-message delay, so precision is the queue's job and poll frequency stops being the ceiling.
- Stamp every message — and the conditional write that marks the Execution row ENQUEUED before pushing — with LeaderLease's **epoch**, so a zombie scheduler's late dispatches are rejectable at the store.
- Stay dumb about execution: the Dispatcher never runs job code; read-and-enqueue is why a single elected tick carries 10k executions/second.

**The invariant it maintains:** **every enqueue carries the epoch under which it was decided.** A zombie's dispatch bearing a stale epoch bounces at the conditional write; whatever it managed to push into the queue anyway is just one more duplicate delivery bearing the same `execution_id`, which the worker's idempotent claim drops.

**Where it breaks.** The queue's ingest quota, before its architecture — an SQS-style default of ~3k messages/second needs raising at target scale. Lands in the forthcoming POC at `06-case-studies/examples/job-scheduler/scheduler/dispatcher.py`.

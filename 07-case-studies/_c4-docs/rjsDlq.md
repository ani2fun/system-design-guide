---
title: Dead-letter queue
kind: Message queue
technology: DLQ
---

## 📮 Dead-letter queue

The **Dead-letter queue** is the circuit breaker for the failure retry cannot fix: determinism. Some jobs fail every time — a bug in the task code, malformed parameters — and without a bound, a poison message loops forever: delivered, crashes the worker, visibility timeout lapses, redelivered, again. Wasted capacity at best; at worst a consumer that spends its life dying. The retry machinery that makes *transient* failures invisible is exactly what makes *deterministic* failures immortal, so a separate exit has to exist.

**Responsibilities**

- Receive any message after **max delivery attempts** (the queue counts receives; ~3 attempts with exponential backoff before giving up), quarantining it so one bad job never blocks the pipeline.
- Page a human — a non-empty DLQ is an alarm, not a backlog. The operator can drop the message, fix the task code, or re-drive it after the fix.
- Keep the user's view honest: the corresponding Execution goes to FAILED with a reason, so the owner sees a failed run in the dashboard instead of wondering why their report never came.

**Where it breaks.** The DLQ round-trip is one of the ways an execution ends up *late through no fault of its schedule* — which is why the misfire policy exists. When a re-driven job finally runs, *"run late or skip?"* is a per-job product decision, not a queue default: a billing run is owed regardless of the outage; forty stale cache warms are pure waste. DLQ depth belongs on the same dashboard as schedule lag, alarmed from zero.

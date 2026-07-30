---
title: Trip service
kind: Service
technology: Python · FastAPI
---

## ⚙️ Trip service

The **Trip service** owns the ride's durable spine: `requested → matched → accepted → en route → in ride → completed`, with failure arrows at every step. Every arrow is a network hop, most involve a human, and the whole process spans an hour — which makes the ride a **workflow**, not a request. The pointed failure case: a driver drops the phone on the passenger seat; who moves on to the next driver if the matcher holding the 10-second timer has meanwhile crashed? Timers, loop position, and retries must survive any single process dying — via durable timeouts (delayed messages) or a durable-execution engine that logs every step and replays past completed ones on recovery.

**Responsibilities**

- Execute state transitions as **conditional writes**: assign a driver only where the ride is still unassigned — this, not the Redis lock, is what makes *"exactly one driver per ride"* true. A zombie matcher's late write matches zero rows and bounces.
- Create each trip **exactly once per request**, backed by the Trip DB's unique constraint, so retried accepts are safe.
- Push status to the rider over the realtime channel at every transition.

**Where it breaks.** At the workflow's external edges: replay and retries only dedupe what the system itself logs, so any outside call — above all payment at `completed → paid` — must expose an idempotent API with caller-supplied keys, or a retry becomes a double charge. Inside the boundary, the DB constraint holds the line.

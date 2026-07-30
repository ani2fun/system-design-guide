# POC: Distributed Job Scheduler

A runnable implementation of the **Design a Distributed Job Scheduler** case
study (`06-case-studies/13-job-scheduler`) — run within seconds of due, never
miss, never double-fire, survive every component dying.

Two decisive containers, five C4 code elements mirrored 1:1:

| Container | C4 code element | File |
| --- | --- | --- |
| Scheduler | `LeaderLease` | [`scheduler/leader_lease.py`](scheduler/leader_lease.py) — lease + monotonic fencing epoch |
| Scheduler | `WindowPoller` | [`scheduler/window_poller.py`](scheduler/window_poller.py) — bounded range read of the due window |
| Scheduler | `Dispatcher` | [`scheduler/dispatcher.py`](scheduler/dispatcher.py) — enqueue with the current epoch (fencing) |
| Worker | `ExecutionClaimer` | [`worker/execution_claimer.py`](worker/execution_claimer.py) — conditional claim, effectively-once |
| Worker | `Heartbeat` | [`worker/heartbeat.py`](worker/heartbeat.py) — extend visibility while running |

Containers: a **FastAPI** service, **Redis** (leader lease + epoch), **Postgres**
(executions). The domain depends on `Coordinator` and `ExecutionStore` ports.

## Run it

```bash
./run            # build + start api (8430) + Redis (8431) + Postgres (8432)
./run test       # mypy --strict + smoke
./run stop
```

## What the smoke proves

- **Leader election** — one node holds the lease; a second is rejected while it
  holds. When the lease lapses, the new leader mints a **higher epoch**.
- **Fencing / double-fire guard** — a dispatch carrying a stale epoch is rejected
  (409); only the current-epoch leader can enqueue. A paused ex-leader can't
  double-fire a job.
- **Effectively-once** — 10 workers racing to claim one execution → **exactly one
  wins** (a conditional `PENDING → RUNNING` UPDATE), turning at-least-once
  delivery into effectively-once execution.
- **Redelivery** — a worker that stops heartbeating loses its visibility lease;
  `reclaim` returns the execution to PENDING and a healthy worker claims it.

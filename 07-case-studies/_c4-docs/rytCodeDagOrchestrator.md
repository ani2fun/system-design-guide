---
title: DagOrchestrator
kind: Code
technology: Python
---

## 🧩 DagOrchestrator

**DagOrchestrator** holds the shape of the work. `expand(video)` turns one upload-complete event into the full task list — split, then one transcode task per segment×rendition pair, then assembly gated behind all of them — and `on_task_done(task)` advances the DAG, dispatching tasks the moment their dependencies clear and calling for assembly when the last transcode reports.

**Responsibilities**

- Expand a video into its segment×rendition task matrix and track DAG state.
- Dispatch a task only when every input-producing task has succeeded — the workflow-scheduler dependency rule.
- Detect dead tasks (worker crash, preemption) and `retry(task)` — at **task** granularity, never restarting the whole video's job for one lost segment.

**The invariant it protects: re-invocation is safe at task granularity.** The orchestrator *will* run tasks more than once — a preempted worker may have written half its output, or all of it, dying before it reported — and it makes no attempt to prevent that. It doesn't have to: every task reads immutable input and writes content-addressed output, so a duplicate execution converges on identical bytes at identical keys. The orchestrator's bookkeeping therefore needs only at-least-once accuracy, which is a radically easier contract than exactly-once dispatch.

In a real system you'd *buy* this class, not build it — Temporal-style orchestrators and the Airflow-lineage schedulers are the category — but knowing what it must do (hold the DAG, gate on dependencies, detect the dead, retry with the idempotence argument) is the interview substance.

**Where it breaks.** Poison videos: a task that crashes every retry must hit a capped-attempts dead-letter path, or one malformed file grinds the fleet. Lands in the forthcoming POC at `06-case-studies/examples/youtube/pipeline/dag_orchestrator.py`.

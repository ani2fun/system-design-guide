---
title: Jobs & executions DB
kind: Wide-column store
technology: DynamoDB / Cassandra
---

## 🧱 Jobs & executions DB

The **Jobs & executions DB** holds the two-table split that *is* this design. A single Jobs table with a `cron_expression` column breaks immediately — finding what's due means evaluating every expression in the database, every tick. So: **Jobs** partitioned by `job_id` (the definitions), and **Executions** partitioned by **hour bucket** — planned time rounded down — so *"what's due in the next five minutes?"* is a range read of one or two partitions, not a table scan. A global secondary index on `user_id` serves the status dashboard without touching the time-bucketed base table.

**Responsibilities**

- Store one Execution row per planned occurrence: `execution_id`, `job_id`, `planned_time`, status (PENDING → RUNNING → COMPLETED / RETRYING / FAILED), attempt count.
- Serve the scheduler's bounded range read: PENDING rows in the current bucket, due within the window.
- Act as the **arbiter of "once"**: the worker's claim is a conditional write PENDING → RUNNING keyed by `execution_id`, and writes carrying a stale fencing epoch are rejected — this is where both duplicate deliveries and zombie schedulers go to die.

Any wide-column or KV store with conditional writes fits — DynamoDB or Cassandra for painless partition scaling; Postgres works with more sharding care. Access patterns matter, not the logo.

**Where it breaks.** Hot buckets: 10k/s × 3,600 s is ~36M rows per hour partition. Rule of thumb: suffix the bucket key with a small hash shard (`bucket#00…#15`) and range-read the suffixes in parallel, or one partition absorbs the whole hour.

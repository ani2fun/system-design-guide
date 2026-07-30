---
title: Reconciliation job
kind: Batch job
technology: Batch (Spark-style)
---

## 🏗️ Reconciliation job

The **Reconciliation job** is why the stream's numbers can be billed against — the principled paranoia after three layers of exactly-once machinery already did their jobs. Checkpoints and idempotent sinks defend against *infrastructure* failures; what slips through is *software*: a transient stream bug, a bad code push, an out-of-order edge case that quietly corrupts counts. Wrongness of that kind is perpetual until something detects and repairs it — so this job periodically recomputes the aggregates from the raw archive, from scratch, and compares against what streaming wrote. It works because batch output is pure derived data, regenerated from immutable input on every run: fix the code, re-run, and the numbers correct themselves — recovery from buggy logic by re-execution, the human fault tolerance batch uniquely offers. Fast-stream plus correct-batch over the same log is the lambda shape; the dashboards run on the stream, the invoices trust this job.

**Responsibilities**

- Read raw click events from the archive on an hourly or nightly cadence and re-aggregate `(ad, minute)` counts end to end — the load is trivial (a 5-minute cadence at peak is ~300 MB per run); the value is independence from the stream's code path.
- Diff against the OLAP store's rows; surface discrepancies for investigation and write corrections — through the same idempotent upsert contract every other writer honors.
- Serve as the continuous audit: run on schedule, not just when an advertiser disputes an invoice.

**Where it breaks.** Two operational taxes: a second system to run, and discrepancy-investigation toil — every diff is a question someone must answer. Accepted knowingly, because the alternative is a billing pipeline with no independent check on itself.

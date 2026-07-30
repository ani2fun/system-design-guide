# POC: Transaction Isolation Anomalies

A runnable companion to **Transactions & isolation**
(`03-distributed-data/03-transactions-and-isolation`). It reproduces two classic
anomalies against a **real Postgres**, then shows the exact guard that prevents
each — because isolation behaviour is defined by the database, not by a
simulation.

| Anomaly | Appears under | Guard that prevents it |
| --- | --- | --- |
| **Lost update** | `READ COMMITTED` read-modify-write | `SELECT … FOR UPDATE` |
| **Write skew** | `REPEATABLE READ` (snapshot) | `SERIALIZABLE` + retry |

| Piece | File | Role |
| --- | --- | --- |
| `LostUpdateExperiment`, `WriteSkewExperiment` | [`domain/experiments.py`](domain/experiments.py) | drive two interleaved transactions; port-only, no SQL |
| `Ledger`, `Session` ports | [`domain/ports.py`](domain/ports.py) | the abstraction the experiments depend on |
| `PostgresSession`, `PostgresLedger` | [`infra/postgres.py`](infra/postgres.py) | asyncpg adapters; translate SQLSTATE 40001 → `SerializationConflict` |

## Run it

```bash
./run            # start Postgres (8441) + run both experiments
./run test       # mypy --strict + smoke (asserts anomaly AND fix)
./run stop       # tear down
```

Uses [`uv`](https://docs.astral.sh/uv/) and Docker. Port block **8441**.

## What the experiments prove

```
== Lost update (start 100, expect 70) ==
  XX  ANOMALY   | Lost update  | READ COMMITTED               | observed=80  expected=70
  OK  prevented | Lost update  | READ COMMITTED + FOR UPDATE  | observed=70  expected=70

== Write skew (constraint: ≥1 doctor on call) ==
  XX  ANOMALY   | Write skew   | REPEATABLE READ              | observed=0   expected=1
  OK  prevented | Write skew   | SERIALIZABLE (+retry)        | observed=1   expected=1
```

Under `READ COMMITTED`, two clients read balance 100, each subtract, and the
second write (computed from the stale 100) clobbers the first — the −10 vanishes.
`FOR UPDATE` makes the second reader block until the first commits, so it reads
90 and correctly lands on 70. Under `REPEATABLE READ`, two on-call doctors each
see "someone else is on call" in their snapshot and both go off — snapshot
isolation permits it because they write *different* rows. `SERIALIZABLE` detects
the read-write cycle (Postgres SSI), aborts the second commit with SQLSTATE
40001, and the retry re-reads the now-correct state and refuses.

## What is simulated vs. real

**Nothing about the isolation is simulated** — that is the whole point. The
transactions run against a genuine Postgres 16; the anomalies and their
prevention are exactly what your production database does at each isolation
level. What this POC *arranges* is the **timing**: instead of hoping two real
clients race at the wrong moment, the experiment holds two connections and
interleaves their statements deterministically (and, for `FOR UPDATE`, runs the
blocking read as an asyncio task to show it waits). So the concurrency is
staged, but the database, the isolation levels, the locks, and the serialization
failure are all real. There is no second machine here — isolation anomalies are
a single-database concurrency phenomenon, not a distributed one; the distributed
cousins (cross-shard transactions) live in the lesson, not this POC.

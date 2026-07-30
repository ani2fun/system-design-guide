# POC: Indexing walkthrough (EXPLAIN ANALYZE)

A runnable walkthrough for the `data-foundations/indexing` lesson: seed a
Postgres table with 200k rows, then run the same query **before and after**
creating an index and read the plan the planner actually chose. The point isn't
the code — it's watching `EXPLAIN (ANALYZE)` flip from a Seq Scan to an Index
Scan (and, for a bad-fit query, refuse to).

Postgres runs in Docker (port **8341**); the harness runs on the host.

## Run it

```bash
./run            # start Postgres, seed, run the walkthrough
./run test       # mypy --strict + smoke (asserts each plan node)
./run stop       # tear down
```

A [`uv`](https://docs.astral.sh/uv/) project (`asyncpg` at runtime, `mypy` for dev).

## The three experiments

| Experiment | Query | Index | Plan flips to |
| --- | --- | --- | --- |
| **Point lookup** | `WHERE user_id = 42` | `(user_id)` | **Index Scan** (from Seq Scan) |
| **Covering / index-only** | `SELECT amount WHERE user_id = 42` | `(user_id) INCLUDE (amount)` | **Index Only Scan** — no heap fetch |
| **Low selectivity** | `WHERE status = 'ok'` (~90% of rows) | `(status)` | **still Seq Scan** — the planner won't use an index that doesn't narrow much |

The third is the one that teaches the most: an index the planner *declines to
use*, because reading 90% of the table through an index is slower than just
scanning it. Indexes help when they're **selective**.

## Design notes (SOLID / DDD)

The I/O boundary — running `EXPLAIN` and reading back the decisive scan node — is
the `QueryPlanner` **port** (`abc.ABC`); `PostgresQueryPlanner` implements it by
parsing `EXPLAIN (ANALYZE, FORMAT JSON)`. `ExperimentRunner` depends only on the
port. `mypy --strict` clean.

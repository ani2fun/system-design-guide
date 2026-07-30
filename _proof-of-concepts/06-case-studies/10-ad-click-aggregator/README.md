# POC: Ad-Click Aggregator (stream aggregation)

A runnable implementation of the **Design an Ad-Click Aggregator** case study
(`06-case-studies/10-ad-click-aggregator`), focused on the stream path: count
clicks at rate, correctly enough to bill on.

The three classes under [`domain/`](domain/) mirror the C4 code elements 1:1:

| C4 code element | File | Role |
| --- | --- | --- |
| `ImpressionDeduper` | [`domain/impression_deduper.py`](domain/impression_deduper.py) | drop duplicate clicks by signed impression id |
| `WindowAggregator` | [`domain/window_aggregator.py`](domain/window_aggregator.py) | event-time tumbling windows + watermark + late corrections |
| `IdempotentSink` | [`domain/idempotent_sink.py`](domain/idempotent_sink.py) | upsert by (ad, window) — replay never double-counts |

Container: a **FastAPI** stream aggregator over **Postgres** (dedup + aggregates
store; a real system uses Kafka + Flink + an OLAP store + a batch reconciler).

## Run it

```bash
./run            # build + start api (8410) + Postgres (8411)
./run test       # mypy --strict + smoke
./run stop
```

## What the smoke proves

- **Event-time windows + watermark** — clicks are bucketed by *when they
  happened*; a window is emitted only once the watermark (max event time seen)
  passes its end, so a window still receiving clicks is held back.
- **Dedup** — a replayed impression id is dropped; the count doesn't move.
- **Late correction** — a click landing in an already-emitted window doesn't
  vanish: the window's count is recomputed and **upserted** (2 → 3), exactly what
  makes replay and late data safe.

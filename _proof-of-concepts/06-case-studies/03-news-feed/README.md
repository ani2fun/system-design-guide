# POC: News Feed (hybrid fan-out)

A runnable implementation of the **Design a News Feed** case study
(`system-design-from-first-principles/06-case-studies/news-feed`), focused on the
decision that defines the design: **who fans out on write, and who merges at
read time.** Normal authors' posts are pushed into each follower's materialized
timeline by a worker; celebrity posts are *skipped* on write and merged into the
feed at read time — the escape from the "one post → tens of millions of writes"
trap.

The four classes mirror, 1:1, the C4 **code**-level elements in
`06-case-studies/news-feed.c4`:

| C4 code element | File | Role |
| --- | --- | --- |
| `TimelineReader` | [`app/timeline_reader.py`](app/timeline_reader.py) | GET /feed: read materialized ids → merge → hydrate |
| `CelebrityMerger` | [`app/celebrity_merger.py`](app/celebrity_merger.py) | read-time: recent posts of the celebrities you follow |
| `FanoutConsumer` | [`worker/fanout_consumer.py`](worker/fanout_consumer.py) | at-least-once consume of post events off the queue |
| `TimelineFanout` | [`worker/timeline_fanout.py`](worker/timeline_fanout.py) | insert post id into each follower's timeline; skip celebrities |

Containers (from the C4 container view): a **FastAPI** feed API, a **separate
fan-out worker** process, a **Postgres** post store + follow graph, a **Redis
Stream** fan-out queue, and a **Redis** timeline cache.

## Run it

```bash
./run            # frees ports 8330–8332, builds, starts api + worker, waits healthy
./run test       # smoke + the hybrid fan-out demonstration
./run stop       # tear down
./run logs worker   # watch the worker fan out
```

Requires Docker (Compose v2). Port block **8330–8332**.

- API → http://localhost:8330 (`/docs`) · Postgres → `localhost:8331` (`feed`/`feed`) · Redis → `localhost:8332`

This is a [`uv`](https://docs.astral.sh/uv/) project (`pyproject.toml` +
`uv.lock`). For editor resolution or running outside Docker: `uv sync
--python 3.12` creates a local `.venv`.

## What to observe

**1. Fan-out on write (the common path).** `POST /posts` inserts the post and
`XADD`s a fan-out event. The worker consumes it, reads the author's followers,
and `ZADD`s the post id into each follower's `timeline:{id}` sorted set.
`GET /timeline/{id}` shows that raw materialized list — the post is *already
there* before the follower ever asks.

**2. Celebrity read-time merge (the escape hatch).** An author with
`>= CELEB_THRESHOLD` followers (3 in this demo) is a celebrity. The worker
**skips** their posts — so they never appear in `GET /timeline/{id}` — yet
`GET /feed?user_id=…` still returns them, tagged `"source": "celebrity-merge"`,
because `CelebrityMerger` live-queries them and `TimelineReader` merges the two
id streams by time.

**3. The arithmetic that forces the hybrid.** Fanning out a celebrity's post to
every follower is O(followers) writes per post. `./run test` proves the split:
the normal post lands in the materialized timeline; the celebrity post does not,
but still shows up in the feed.

```bash
./run test        # SAFE demonstration of both paths + ordering
# or by hand:
curl -s -XPOST localhost:8330/posts -H 'content-type: application/json' -d '{"author_id":2,"content":"x"}'
curl -s localhost:8330/timeline/1 | python3 -m json.tool   # materialized (fanned-out) ids
curl -s 'localhost:8330/feed?user_id=1' | python3 -m json.tool  # merged + hydrated, with source tags
```

**4. At-least-once + idempotent.** The worker reads via a Redis Stream consumer
group (at-least-once) and `XACK`s. The timeline insert is `ZADD` keyed by post
id, so a redelivered event re-inserts the *same* member — no duplicates.

## Notes & simplifications

- `CELEB_THRESHOLD=3` so a celebrity is trivial to create in a test; real systems
  use a much higher bar (and often per-author flags).
- Timelines are capped to the newest `TIMELINE_MAX` ids (`ZREMRANGEBYRANK`).
- Post ids are a Postgres `BIGSERIAL`, so id order ≈ time order — which is why
  the timeline sorted set can use the id itself as the score.
- One image runs both roles; compose starts it twice (api + worker) with
  different commands. The worker waits for the API so the schema exists first.

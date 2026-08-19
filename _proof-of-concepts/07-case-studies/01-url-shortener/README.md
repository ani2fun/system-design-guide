# POC: URL Shortener

A runnable implementation of the **Design a URL Shortener** case study
(`system-design-from-first-principles/06-case-studies/url-shortener`). The four
classes here mirror, 1:1, the C4 **code**-level elements in
`06-case-studies/url-shortener.c4` — so the diagram you read *is* this code's map.

| C4 code element | File | Role |
| --- | --- | --- |
| `LinkCreator` | [`app/link_creator.py`](app/link_creator.py) | `POST /links`: validate → next id → encode → insert |
| `Base62Codec` | [`app/base62_codec.py`](app/base62_codec.py) | pure counter-id ↔ short-code (no I/O) |
| `RangeLease` | [`app/range_lease.py`](app/range_lease.py) | leases disjoint counter ranges by atomic fetch-and-add |
| `RedirectHandler` | [`app/redirect_handler.py`](app/redirect_handler.py) | `GET /{code}`: cache → store → 302, fire-and-forget click |

Containers (from the C4 container view): a stateless **FastAPI** API, a
**Redis** redirect cache, a **Postgres** link store, a Postgres **id range
allocator** row, and a **Redis Stream** click feed.

## Run it

```bash
./run            # frees ports 8310–8312, builds, starts, waits healthy
./run test       # pure unit tests + end-to-end smoke
./run stop       # tear down
```

Requires Docker (Compose v2). Port block **8310–8312** — chosen never to
collide with the synapse stack or the other POCs.

This is a [`uv`](https://docs.astral.sh/uv/) project (`pyproject.toml` +
`uv.lock`). For editor resolution or running outside Docker: `uv sync
--python 3.12` creates a local `.venv`, then e.g. `uv run uvicorn app.main:app`.

- API → http://localhost:8310 (OpenAPI docs at `/docs`)
- Postgres → `localhost:8311` (`shortener`/`shortener`)
- Redis → `localhost:8312`

## What to observe (the design, made concrete)

**1. Range leasing — a global counter without a global hot row.**
Each API process leases a batch of ids (`RANGE_BATCH=1000`) with one atomic
`UPDATE … SET next_value = next_value + 1000 … RETURNING next_value`, then hands
them out locally. Create 5 links and watch `/stats`: `ids_issued` climbs but
`ranges_leased` stays at 1 until the batch is exhausted — the allocator row is
touched once per *thousand* writes, not once per write.

```bash
for i in $(seq 1 5); do
  curl -s -XPOST localhost:8310/links -H 'content-type: application/json' \
       -d "{\"url\":\"https://example.com/p/$i\"}"; echo
done
curl -s localhost:8310/stats | python3 -m json.tool
```

Restart the API (`docker compose restart api`) and create another link: the new
code jumps forward by a whole batch. That gap is the crash-safety property —
**leased-but-unused ids are lost, never reissued**, so codes are unique without
coordination.

**2. Cache absorbs the read skew.** The first `GET /{code}` is a cache miss
(reads Postgres, populates Redis); every subsequent hit is served from Redis.
Hammer one code and watch `hit_ratio` climb toward 1.0:

```bash
code=$(curl -s -XPOST localhost:8310/links -H 'content-type: application/json' \
       -d '{"url":"https://example.com/hot"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["code"])')
for i in $(seq 1 200); do curl -s -o /dev/null localhost:8310/$code; done
curl -s localhost:8310/stats | python3 -m json.tool   # redirect.hit_ratio ~0.99
```

**3. Clicks are fire-and-forget.** Every redirect `XADD`s to the `clicks` Redis
Stream *without* the response awaiting it. Inspect the stream:

```bash
docker compose exec redis redis-cli XLEN clicks
docker compose exec redis redis-cli XRANGE clicks - + COUNT 3
```

## Notes & simplifications

- One API replica by default. To *see* disjoint ranges across replicas, scale
  it (`docker compose up -d --scale api=3` — note Compose will round-robin the
  single published port) and observe that no two processes ever issue the same
  id.
- The click stream is written but not consumed here — the analytics/aggregation
  pipeline is out of scope for this POC (see the Ad Click Aggregator case study).
- `COUNTER_START=1_000_000` so the first codes are ~4 chars rather than 1.

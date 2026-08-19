# POC: Web Crawler (the URL frontier)

A runnable implementation of the **Design a Web Crawler** case study
(`06-case-studies/08-web-crawler`), focused on the frontier — the "brain" that
decides *which URL to fetch next* without hammering any host or re-crawling the
web into itself.

The three classes under [`domain/`](domain/) mirror the C4 code elements 1:1:

| C4 code element | File | Role |
| --- | --- | --- |
| `FrontierScheduler` | [`domain/frontier_scheduler.py`](domain/frontier_scheduler.py) | rotate across hosts; hand out the next politeness-gated URL |
| `PolitenessGate` | [`domain/politeness_gate.py`](domain/politeness_gate.py) | robots rules + per-host rate gate (`SET NX PX`) |
| `UrlDeduper` | [`domain/url_deduper.py`](domain/url_deduper.py) | normalize + drop already-seen (the loop-breaker) |

Container: a **FastAPI** frontier over **Redis** (seen set + per-host queues +
per-host gate).

## Run it

```bash
./run            # build + start api (8390) + Redis (8391)
./run test       # mypy --strict + smoke
./run stop
```

## What the smoke proves

- **Dedup + robots** — five seed URLs (three of which normalize to the same, one
  robots-disallowed) admit **two**. Normalization collapses `#fragments`,
  trailing slashes, and case.
- **Domain rotation** — `/next` visits distinct hosts round-robin, so no single
  host monopolizes the fetchers.
- **Per-host politeness** — after dispatching a URL for a host, a second `/next`
  for that host returns nothing (the gate is closed) until the interval elapses —
  the per-host `SET NX PX` rate limit in action.

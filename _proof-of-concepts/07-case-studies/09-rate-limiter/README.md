# POC: Rate Limiter

A runnable implementation of the **Design a Rate Limiter** case study
(`06-case-studies/09-rate-limiter`) — one allow/deny decision, made correctly
under concurrency, in one atomic round-trip.

The three classes under [`domain/`](domain/) mirror the C4 code elements 1:1:

| C4 code element | File | Role |
| --- | --- | --- |
| `RuleResolver` | [`domain/rule_resolver.py`](domain/rule_resolver.py) | key/tier → applicable rule (cached, prefix match) |
| `WindowAlgorithm` | [`domain/window_algorithm.py`](domain/window_algorithm.py) | dispatch to fixed window / sliding window / token bucket |
| `AtomicCounter` | [`domain/atomic_counter.py`](domain/atomic_counter.py) | each algorithm is one atomic Lua script — the race-killer |

Container: a **FastAPI** limiter over **Redis** (counter state). The algorithm
logic lives as Lua *in the domain*; the `ScriptRunner` port only executes it.

## Run it

```bash
./run            # build + start api (8400) + Redis (8401)
./run test       # mypy --strict + smoke
./run stop
```

## What the smoke proves

- **Fixed window** — a `limit=5` key admits 5, then denies.
- **Rule tiers** — a `vip:` key (limit 100) admits all; a `free:` key (limit 5)
  doesn't. `RuleResolver` picks by prefix.
- **Atomicity** — 20 requests fired concurrently at a `limit=5` key admit
  **exactly 5**. Check-and-increment as one Lua script closes the race a
  read-then-write from the app would lose.
- **Token bucket** — a capacity-3 bucket admits a burst of 3, then denies the
  4th until it refills.

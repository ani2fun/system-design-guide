# POC: Load-Balancing Strategies

A runnable companion to **Load balancing & gateways**
(`04-building-blocks/01-load-balancing-and-gateways`). It routes one identical
request stream through five strategies and measures the number that actually
matters: the **peak concurrent load on the busiest backend**, which is what sets
your tail latency.

| Strategy | File symbol | Idea |
| --- | --- | --- |
| Round-robin | `RoundRobin` | rotate; even counts, blind to load |
| Random | `RandomChoice` | pick one at random; the blind baseline |
| Least-connections | `LeastConnections` | route to the fewest in-flight (random tie-break) |
| Power-of-two-choices | `PowerOfTwoChoices` | sample 2, take the lighter — O(1) state |
| Consistent hash | `ConsistentHash` | sticky per client key (affinity), ring with vnodes |

All live in [`domain/strategies.py`](domain/strategies.py) behind one
`LoadBalancer` port; the discrete-event simulation is
[`domain/simulation.py`](domain/simulation.py).

## Run it

```bash
./run            # compare five strategies on tail load
./run test       # mypy --strict + unit tests + demo
./run check      # mypy only
```

Uses [`uv`](https://docs.astral.sh/uv/); no Docker, no ports, standard library only.

## What the demo proves

```
30000 requests, 16 backends, exponential service (mean 11), ~0.69 load
  round-robin        peak max=4   handled 1875–1875
  random             peak max=7   handled 1829–1930
  least-connections  peak max=2   handled 1795–1976   <- best tail
  power-of-two       peak max=3   handled 1844–1927   <- near-best, O(1) state
  consistent-hash    peak max=9   handled 1260–2640   <- stickiness costs balance
```

The lesson's claims fall out as numbers: routing **blind to load** (random) runs
the hottest tail; **rotating** (round-robin) helps but still ignores that one
backend drew several long requests; **load-aware** strategies (least-connections,
power-of-two) hold the lowest peak — and power-of-two gets within one of full
least-connections while only ever inspecting *two* backends, the classic "power
of two choices" result. Consistent hashing deliberately accepts a worse peak to
keep each client pinned to one backend (session/cache affinity).

## What is simulated vs. real

A real load balancer (nginx, HAProxy, Envoy, an AWS ALB) spreads requests across
**many backend machines** and watches their live connection counts. This POC
**mimics the backends in one process**: each is a `Backend` object with an
`inflight` counter, and a virtual clock advances request-by-request — releasing
finished requests before each routing decision so `inflight` is exact. There are
no real sockets, no network, and no wall-clock time; service durations are drawn
from an exponential distribution to stand in for variable request cost.

What is **identical to production**: the routing algorithms themselves. `choose`
implements round-robin, least-connections, power-of-two, and a consistent-hash
ring exactly as a real proxy would; the peak-load ordering you see is the same
ordering these algorithms produce on real traffic. Only the "backend" (an object
instead of a server) and the clock (virtual instead of wall-clock) are faked.
Health checking, connection draining, and retries live in the lesson, not here.

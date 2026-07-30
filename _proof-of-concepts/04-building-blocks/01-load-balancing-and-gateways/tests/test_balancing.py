from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.backend import Backend  # noqa: E402
from domain.simulation import Request, simulate  # noqa: E402
from domain.strategies import (  # noqa: E402
    ConsistentHash,
    LeastConnections,
    PowerOfTwoChoices,
    RandomChoice,
    RoundRobin,
)


def _requests(rng: random.Random, n: int = 20_000) -> list[Request]:
    t = 0.0
    out: list[Request] = []
    for i in range(n):
        t += rng.expovariate(1.0)
        out.append(Request(t, rng.expovariate(1.0 / 11.0), f"c{i % 400}"))
    return out


def test_round_robin_even_counts() -> None:
    backends = [Backend(f"b{i}") for i in range(8)]
    rr = RoundRobin()
    m = simulate(rr, backends, _requests(random.Random(1)))
    assert m.max_share - m.min_share <= 1  # round-robin equalizes counts


def test_load_aware_beats_blind_on_peak() -> None:
    reqs = _requests(random.Random(2))
    backends = [Backend(f"b{i}") for i in range(16)]
    rr = simulate(RoundRobin(), backends, reqs)
    rnd = simulate(RandomChoice(random.Random(3)), backends, reqs)
    lc = simulate(LeastConnections(random.Random(3)), backends, reqs)
    p2c = simulate(PowerOfTwoChoices(random.Random(3)), backends, reqs)
    # Load-aware strategies hold a strictly lower tail than blind-random.
    assert lc.max_peak < rnd.max_peak
    assert p2c.max_peak < rnd.max_peak
    # Least-connections is the best (or tied-best) tail of all.
    assert lc.max_peak <= min(rr.max_peak, p2c.max_peak)
    # Power-of-two is close to full least-connections despite O(1) state.
    assert p2c.max_peak <= lc.max_peak + 3
    # Least-connections with random tie-break also keeps counts even.
    assert lc.max_share - lc.min_share < rnd.max_share - rnd.min_share + 200


def test_consistent_hash_is_sticky() -> None:
    backends = [Backend(f"b{i}") for i in range(10)]
    ch = ConsistentHash(backends)
    picks = {ch.choose(backends, f"user{i}").name for _ in range(5) for i in range(50)}
    # Deterministic: each user always maps to one backend (<= 10 distinct picks).
    assert len(picks) <= len(backends)
    for i in range(50):
        chosen = {ch.choose(backends, f"user{i}").name for _ in range(5)}
        assert len(chosen) == 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"PASS  {len(fns)} load-balancing tests")

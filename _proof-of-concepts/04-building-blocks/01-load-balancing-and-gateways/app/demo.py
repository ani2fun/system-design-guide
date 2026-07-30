"""Demo — route one identical request stream through five strategies and compare
their tail load (peak concurrent requests on the busiest backend). Round-robin
and random ignore load; least-connections and power-of-two track it; consistent
hashing trades balance for stickiness.

Run: `./run demo`
"""

from __future__ import annotations

import random

from domain.backend import Backend
from domain.simulation import Request, simulate
from domain.strategies import (
    ConsistentHash,
    LeastConnections,
    LoadBalancer,
    PowerOfTwoChoices,
    RandomChoice,
    RoundRobin,
)

BACKENDS = 16
REQUESTS = 30_000
CLIENTS = 500
ARRIVAL_RATE = 1.0      # mean inter-arrival 1.0 time unit
SERVICE_MEAN = 11.0     # heavy, variable service → ~0.69 utilization on 16 backends


def make_requests(rng: random.Random) -> list[Request]:
    t = 0.0
    out: list[Request] = []
    for i in range(REQUESTS):
        t += rng.expovariate(ARRIVAL_RATE)
        service = rng.expovariate(1.0 / SERVICE_MEAN)  # exponential: some very long
        out.append(Request(t, service, f"client:{i % CLIENTS}"))
    return out


def main() -> None:
    rng = random.Random(42)
    requests = make_requests(rng)
    backends = [Backend(f"b{i}") for i in range(BACKENDS)]

    strategies: list[LoadBalancer] = [
        RoundRobin(),
        RandomChoice(random.Random(7)),
        LeastConnections(random.Random(7)),
        PowerOfTwoChoices(random.Random(7)),
        ConsistentHash(backends),
    ]

    print(f"== {REQUESTS} requests, {BACKENDS} backends, exponential service "
          f"(mean {SERVICE_MEAN:.0f}), ~0.69 load ==")
    print("   lower peak = better balancing; the busiest backend sets your tail latency\n")
    for strat in strategies:
        print(simulate(strat, backends, requests).render())

    print("\nRead it as: least-connections and power-of-two hold the lowest peak with")
    print("O(1) state; round-robin/random run hotter because they route blind to load;")
    print("consistent-hash accepts a higher peak to keep each client sticky to a backend.")


if __name__ == "__main__":
    main()

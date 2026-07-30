"""A discrete-event simulation of a request stream flowing through a load
balancer onto a pool of backends. No real time or threads: a virtual clock
advances request-by-request, releasing finished requests before each routing
decision so `inflight` is accurate. Pure domain logic over the strategy port.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

from domain.backend import Backend
from domain.strategies import LoadBalancer


@dataclass(frozen=True)
class Request:
    arrival: float
    service: float
    key: str


@dataclass(frozen=True)
class Metrics:
    strategy: str
    max_peak: int      # worst backend's peak concurrent load (the tail)
    avg_peak: float    # mean peak across backends
    max_share: int     # most requests any single backend handled
    min_share: int     # fewest

    def render(self) -> str:
        return (f"  {self.strategy:<18} peak: max={self.max_peak:<3} "
                f"avg={self.avg_peak:>4.1f}   handled: "
                f"{self.min_share}–{self.max_share} per backend")


def simulate(strategy: LoadBalancer, backends: list[Backend], requests: list[Request]) -> Metrics:
    for b in backends:
        b.inflight = b.handled = b.peak = 0

    completions: list[tuple[float, int, Backend]] = []
    seq = 0
    for req in requests:
        while completions and completions[0][0] <= req.arrival:
            _, _, done = heapq.heappop(completions)
            done.finish()
        chosen = strategy.choose(backends, req.key)
        chosen.start()
        heapq.heappush(completions, (req.arrival + req.service, seq, chosen))
        seq += 1

    peaks = [b.peak for b in backends]
    shares = [b.handled for b in backends]
    return Metrics(
        strategy=strategy.name,
        max_peak=max(peaks),
        avg_peak=sum(peaks) / len(peaks),
        max_share=max(shares),
        min_share=min(shares),
    )

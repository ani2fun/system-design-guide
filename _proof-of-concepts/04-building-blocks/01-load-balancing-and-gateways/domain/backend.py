"""Backend — a simulated server behind the load balancer.

`inflight` is the number of requests currently being served (the signal
connection-aware strategies use); `handled` and `peak` are metrics the
simulation accumulates.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Backend:
    name: str
    inflight: int = 0
    handled: int = 0
    peak: int = 0

    def start(self) -> None:
        self.inflight += 1
        self.handled += 1
        self.peak = max(self.peak, self.inflight)

    def finish(self) -> None:
        self.inflight -= 1

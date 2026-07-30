"""WindowAlgorithm — the algorithm zoo behind one interface (C4 code element).

Dispatches a rule to the right atomic script. Each algorithm has its own burst
personality; the caller just asks "allow this key under this rule?".
"""

from __future__ import annotations

import time

from domain.atomic_counter import AtomicCounter
from domain.model import Algorithm, Decision, Rule


class WindowAlgorithm:
    def __init__(self, counter: AtomicCounter) -> None:
        self._counter = counter

    async def check(self, key: str, rule: Rule) -> Decision:
        now_ms = int(time.time() * 1000)
        if rule.algorithm is Algorithm.FIXED:
            return await self._counter.fixed_window(key, rule.limit, rule.window_ms)
        if rule.algorithm is Algorithm.SLIDING:
            return await self._counter.sliding_window(key, rule.limit, rule.window_ms, now_ms)
        refill_per_ms = rule.limit / rule.window_ms
        return await self._counter.token_bucket(key, rule.limit, refill_per_ms, now_ms)

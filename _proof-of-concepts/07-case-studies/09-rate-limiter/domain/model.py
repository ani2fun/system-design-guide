"""Rate-limiter domain model (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Algorithm(str, Enum):
    FIXED = "fixed"       # fixed window
    SLIDING = "sliding"   # sliding-window log
    BUCKET = "bucket"     # token bucket


@dataclass(frozen=True, slots=True)
class Rule:
    algorithm: Algorithm
    limit: int            # requests per window (= bucket capacity)
    window_ms: int        # window length (= time to refill a full bucket)


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    remaining: int
    retry_after_ms: int

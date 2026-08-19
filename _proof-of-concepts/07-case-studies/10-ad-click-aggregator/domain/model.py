"""Stream-aggregator domain model (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Click:
    ad_id: str
    impression_id: str   # signed identity — the dedup key
    event_time_ms: int   # when the click happened (event time, not arrival time)


@dataclass(frozen=True, slots=True)
class WindowCount:
    ad_id: str
    window_start_ms: int
    count: int

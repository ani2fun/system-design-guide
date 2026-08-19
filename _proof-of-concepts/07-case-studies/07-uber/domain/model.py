"""Matching-service domain model (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MatchResult:
    request_id: str
    driver_id: str
    trip_id: int

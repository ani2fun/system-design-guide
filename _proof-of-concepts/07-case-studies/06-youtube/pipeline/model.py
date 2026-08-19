"""Transcoding-pipeline domain model (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Progress:
    video: str
    tasks_total: int   # segments × renditions
    tasks_done: int    # renditions that physically exist (content-addressed)
    state: str         # 'processing' | 'live'

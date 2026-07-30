"""Scheduler domain model (no I/O)."""

from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


class StaleEpochError(Exception):
    """A fencing check failed: the actor's epoch is older than the current leader's."""

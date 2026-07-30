"""Device-side domain model (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chunk:
    hash: str        # content hash = identity
    data: bytes


@dataclass(frozen=True, slots=True)
class SyncResult:
    chunks_total: int   # chunks in the file
    changed: int        # chunks not in the previous manifest
    uploaded: int       # chunks actually sent (changed − already on the server = dedup)

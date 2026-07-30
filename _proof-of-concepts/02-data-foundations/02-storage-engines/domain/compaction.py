"""Compactor — merges segments, keeping the newest value per key.

A k-way merge over segments (passed newest-first): the first value seen for a
key wins, and tombstones are dropped entirely (safe here because compaction
merges *all* live segments — no older copy survives elsewhere). This is what
reclaims the space spent by overwrites and deletes.
"""

from __future__ import annotations

from domain.model import Entry
from domain.sstable import SSTable


class Compactor:
    def merge(self, newest_first: list[SSTable]) -> list[Entry]:
        latest: dict[str, Entry] = {}
        for segment in newest_first:
            for entry in segment.scan():
                latest.setdefault(entry.key, entry)  # first (newest) wins
        return [latest[k] for k in sorted(latest) if not latest[k].is_tombstone]

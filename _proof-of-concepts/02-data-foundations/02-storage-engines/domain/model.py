"""Domain model — the unit an LSM engine stores.

An `Entry` is a key bound to a value, or to a **tombstone** (`value is None`) —
a delete marker that shadows older values until compaction drops it. Keys and
values are strings to keep the toy legible.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Entry:
    key: str
    value: str | None  # None ⇒ tombstone (deleted)

    @property
    def is_tombstone(self) -> bool:
        return self.value is None

"""Memtable — the in-memory write buffer at the top of the LSM.

Writes land here (including tombstones); on reaching a size threshold it is
flushed as a sorted, immutable SSTable. A dict keeps the latest value per key;
sorting happens once, at flush.
"""

from __future__ import annotations

from domain.model import Entry


class Memtable:
    def __init__(self) -> None:
        self._data: dict[str, str | None] = {}

    def put(self, key: str, value: str | None) -> None:
        self._data[key] = value

    def get(self, key: str) -> Entry | None:
        if key in self._data:
            return Entry(key, self._data[key])
        return None

    def __len__(self) -> int:
        return len(self._data)

    def sorted_entries(self) -> list[Entry]:
        return [Entry(k, self._data[k]) for k in sorted(self._data)]

    def clear(self) -> None:
        self._data.clear()

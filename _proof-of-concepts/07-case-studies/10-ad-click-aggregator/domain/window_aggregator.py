"""WindowAggregator — event-time tumbling windows + watermark (C4 code element).

Each click falls into a fixed window by its event time. A watermark
(max event time seen − allowed lateness) decides when a window is 'closed'
enough to emit. `flush` yields closed windows whose count is new or has changed —
so a late click landing in an already-emitted window produces a **correction**,
not a lost count. State is in-memory here (a real engine checkpoints it).
"""

from __future__ import annotations

from domain.model import WindowCount


class WindowAggregator:
    def __init__(self, window_ms: int, lateness_ms: int = 0) -> None:
        self._window = window_ms
        self._lateness = lateness_ms
        self._counts: dict[tuple[str, int], int] = {}
        self._emitted: dict[tuple[str, int], int] = {}
        self._watermark = 0

    def add(self, ad_id: str, event_time_ms: int) -> None:
        window = (event_time_ms // self._window) * self._window
        self._counts[(ad_id, window)] = self._counts.get((ad_id, window), 0) + 1
        self._watermark = max(self._watermark, event_time_ms - self._lateness)

    def flush(self) -> list[WindowCount]:
        out: list[WindowCount] = []
        for (ad_id, window), count in self._counts.items():
            closed = window + self._window <= self._watermark
            if closed and self._emitted.get((ad_id, window)) != count:
                self._emitted[(ad_id, window)] = count
                out.append(WindowCount(ad_id, window, count))
        return out

    def reset(self) -> None:
        self._counts.clear()
        self._emitted.clear()
        self._watermark = 0

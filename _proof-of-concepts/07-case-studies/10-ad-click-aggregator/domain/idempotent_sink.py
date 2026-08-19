"""IdempotentSink — upsert aggregates by (ad, window) (C4 code element).

Emitting the same closed window again (checkpoint replay, or a correction)
overwrites the row rather than adding to it, so recovery never double-counts.
"""

from __future__ import annotations

from domain.model import WindowCount
from domain.ports import AggregateSink


class IdempotentSink:
    def __init__(self, sink: AggregateSink) -> None:
        self._sink = sink

    async def emit(self, window: WindowCount) -> None:
        await self._sink.upsert(window.ad_id, window.window_start_ms, window.count)

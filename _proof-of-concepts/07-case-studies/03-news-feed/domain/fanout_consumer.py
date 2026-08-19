"""FanoutConsumer — at-least-once delivery of post events off the queue (C4 code element).

Polls the FanoutQueue port, hands each event to TimelineFanout, and acks. The
queue gives at-least-once delivery; the fan-out's idempotent insert makes a
redelivery safe.
"""

from __future__ import annotations

from domain.ports import FanoutQueue
from domain.timeline_fanout import TimelineFanout


class FanoutConsumer:
    def __init__(self, queue: FanoutQueue, fanout: TimelineFanout) -> None:
        self._queue = queue
        self._fanout = fanout
        self.processed = 0

    async def run_once(self, count: int = 50, block_ms: int = 2000) -> int:
        events = await self._queue.poll(count, block_ms)
        for event in events:
            await self._fanout.fanout(event.post_id, event.author_id)
            await self._queue.ack(event.msg_id)
            self.processed += 1
        return len(events)

    async def run_forever(self) -> None:
        await self._queue.ensure_group()
        while True:
            await self.run_once()

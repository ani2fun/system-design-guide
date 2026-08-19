"""InMemoryBroker — a simulated message bus. Every publish is appended to an
append-only log (like a Kafka partition), so duplicates published by the relay
are visible as repeated entries. A consumer drains from a moving offset.
"""

from __future__ import annotations

from domain.model import OutboxEvent
from domain.ports import Broker
from domain.services import IdempotentConsumer


class InMemoryBroker(Broker):
    def __init__(self) -> None:
        self.log: list[OutboxEvent] = []  # append-only; may contain duplicates

    async def publish(self, topic: str, event: OutboxEvent) -> None:
        self.log.append(event)

    async def deliver_new(self, consumer: IdempotentConsumer, offset: int) -> int:
        """Deliver every message past `offset` to the consumer; return the new
        offset (i.e. len(log))."""
        for event in self.log[offset:]:
            await consumer.handle(event)
        return len(self.log)

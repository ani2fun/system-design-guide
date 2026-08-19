"""The three services that make up the pattern — all pure domain logic over the
ports:

* `OrderService` writes the order and its event in one transaction (no dual write).
* `OutboxRelay` polls unsent events, publishes them, and marks them sent —
  at-least-once, because a crash between publish and mark re-publishes.
* `IdempotentConsumer` dedups on `event_id`, turning at-least-once delivery into
  effectively-once processing.
"""

from __future__ import annotations

from collections.abc import Callable

from domain.model import Order, OutboxEvent, SimulatedCrash
from domain.ports import Broker, UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]


class OrderService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def place_order(self, order: Order) -> None:
        order.validate()  # raises InvalidOrder → nothing is written
        async with self._uow_factory() as uow:
            await uow.orders.add(order)
            await uow.outbox.add(order.placed_event())  # same transaction
            await uow.commit()


class OutboxRelay:
    def __init__(self, uow_factory: UnitOfWorkFactory, broker: Broker, topic: str = "orders") -> None:
        self._uow_factory = uow_factory
        self._broker = broker
        self._topic = topic

    async def run_once(self, *, limit: int = 100, crash_before_mark: bool = False) -> int:
        """Publish a batch of unsent events. Returns how many were published.
        If `crash_before_mark`, the transaction rolls back after publishing —
        so the events stay unsent and a later run publishes them again."""
        async with self._uow_factory() as uow:
            records = await uow.outbox.fetch_unsent(limit)
            for record in records:
                await self._broker.publish(self._topic, record.event)  # external — not in the tx
            if crash_before_mark:
                raise SimulatedCrash("relay died after publish, before mark_sent")
            await uow.outbox.mark_sent([r.seq for r in records])
            await uow.commit()
            return len(records)


class IdempotentConsumer:
    """Applies each event's side effect exactly once, even if the broker delivers
    duplicates, by remembering the event_ids it has already processed."""

    def __init__(self) -> None:
        self._processed: set[str] = set()
        self.applied: list[str] = []   # aggregate_ids whose effect actually ran

    async def handle(self, event: OutboxEvent) -> bool:
        if event.event_id in self._processed:
            return False  # duplicate — absorbed
        self._processed.add(event.event_id)
        self.applied.append(event.aggregate_id)
        return True

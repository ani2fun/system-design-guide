"""Smoke test — assert the outbox guarantees: atomicity, at-least-once delivery,
and effectively-once processing through the idempotent consumer. Requires
Postgres up (./run test)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import PG_DSN  # noqa: E402
from domain.model import InvalidOrder, Order, SimulatedCrash  # noqa: E402
from domain.services import IdempotentConsumer, OrderService, OutboxRelay  # noqa: E402
from infra.broker import InMemoryBroker  # noqa: E402
from infra.postgres import UnitOfWorkFactory, connect  # noqa: E402


async def main() -> None:
    pool = await connect(PG_DSN)
    try:
        uow_factory = UnitOfWorkFactory(pool)
        service = OrderService(uow_factory)
        broker = InMemoryBroker()
        relay = OutboxRelay(uow_factory, broker)
        consumer = IdempotentConsumer()
        offset = 0

        # Atomic writes → clean relay → one effect per order.
        for i in range(5):
            await service.place_order(Order(f"o{i}", f"c{i}", (i + 1) * 100))
        assert await relay.run_once() == 5
        offset = await broker.deliver_new(consumer, offset)
        assert len(consumer.applied) == 5
        print("  ok  atomic write + relay: 5 orders → 5 effects")

        # Rejected order writes no event.
        try:
            await service.place_order(Order("bad", "c", 0))
        except InvalidOrder:
            pass
        assert await relay.run_once() == 0
        print("  ok  atomicity: failed order left no orphan event")

        # Crash after publish → duplicates on the bus, absorbed by the consumer.
        for i in range(5, 7):
            await service.place_order(Order(f"o{i}", f"c{i}", (i + 1) * 100))
        try:
            await relay.run_once(crash_before_mark=True)
        except SimulatedCrash:
            pass
        assert len(broker.log) == 7          # 5 + 2 published before the crash
        assert await relay.run_once() == 2   # retry republishes the same 2
        assert len(broker.log) == 9          # 2 duplicates now on the bus
        offset = await broker.deliver_new(consumer, offset)
        assert len(consumer.applied) == 7                 # only 7 unique effects
        assert len(set(consumer.applied)) == 7            # for 7 distinct orders
        print("  ok  crash re-delivery: 9 messages, 2 duplicates, 7 effects (once each)")

        print("PASS  transactional outbox: atomic, at-least-once, effectively-once")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())

"""Composition root — walk through the transactional outbox: atomic write, clean
relay, an atomicity failure, and a relay crash that re-delivers (absorbed by the
idempotent consumer).

Run: `./run` (starts Postgres) or `./run demo` (Postgres already up).
"""

from __future__ import annotations

import asyncio

from app.config import PG_DSN
from domain.model import InvalidOrder, Order, SimulatedCrash
from domain.services import IdempotentConsumer, OrderService, OutboxRelay
from infra.broker import InMemoryBroker
from infra.postgres import UnitOfWorkFactory, connect


async def main() -> None:
    pool = await connect(PG_DSN)
    try:
        uow_factory = UnitOfWorkFactory(pool)
        service = OrderService(uow_factory)
        broker = InMemoryBroker()
        relay = OutboxRelay(uow_factory, broker)
        consumer = IdempotentConsumer()
        offset = 0

        print("== 1. Atomic write: order + event commit together ==")
        for i in range(5):
            await service.place_order(Order(f"o{i}", f"cust{i}", (i + 1) * 100))
        print("  placed 5 orders; each wrote an OrderPlaced event in the same transaction")

        print("\n== 2. Relay publishes the outbox, consumer applies effects ==")
        published = await relay.run_once()
        offset = await broker.deliver_new(consumer, offset)
        print(f"  relay published {published}; broker log={len(broker.log)}; "
              f"consumer applied {len(consumer.applied)} effects")

        print("\n== 3. Atomicity: a rejected order writes NEITHER row nor event ==")
        try:
            await service.place_order(Order("bad", "cust", 0))  # amount 0 → InvalidOrder
        except InvalidOrder as exc:
            print(f"  rejected ({exc}); relay finds nothing new to publish:")
        published = await relay.run_once()
        print(f"  relay published {published} (no orphan event from the failed order)")

        print("\n== 4. Relay crash after publish, before mark → re-delivery ==")
        for i in range(5, 7):
            await service.place_order(Order(f"o{i}", f"cust{i}", (i + 1) * 100))
        try:
            await relay.run_once(crash_before_mark=True)  # publishes 2, then dies
        except SimulatedCrash as exc:
            print(f"  crash: {exc}")
        print(f"  broker log={len(broker.log)} (the 2 events ARE on the bus, but unmarked)")
        published = await relay.run_once()  # retry → republishes the same 2
        offset = await broker.deliver_new(consumer, offset)
        print(f"  retry republished {published}; broker log={len(broker.log)} "
              f"(2 duplicates delivered)")

        print(f"\nResult: broker delivered {len(broker.log)} messages, consumer applied "
              f"{len(consumer.applied)} unique effects for {len(set(consumer.applied))} orders.")
        print("At-least-once delivery + idempotent consumer = effectively-once processing.")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())

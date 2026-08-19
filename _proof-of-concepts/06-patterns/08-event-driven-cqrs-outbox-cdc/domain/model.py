"""Domain model — an order aggregate, the outbox event that must be written in
the *same* transaction as the order, and the two exceptions the flow uses.
"""

from __future__ import annotations

from dataclasses import dataclass


class InvalidOrder(Exception):
    """The order failed a business rule; nothing (order or event) is written."""


class SimulatedCrash(Exception):
    """Injected to model the relay dying after publishing but before marking
    events sent — the failure the outbox pattern is designed to survive."""


@dataclass(frozen=True)
class Order:
    id: str
    customer: str
    amount_cents: int

    def validate(self) -> None:
        if self.amount_cents <= 0:
            raise InvalidOrder(f"order {self.id}: amount must be positive")

    def placed_event(self) -> OutboxEvent:
        return OutboxEvent(
            event_id=f"evt-{self.id}",
            aggregate_id=self.id,
            type="OrderPlaced",
            payload=f'{{"order":"{self.id}","customer":"{self.customer}",'
                    f'"amount_cents":{self.amount_cents}}}',
        )


@dataclass(frozen=True)
class OutboxEvent:
    event_id: str        # stable, unique — the consumer dedups on this
    aggregate_id: str
    type: str
    payload: str


@dataclass(frozen=True)
class OutboxRecord:
    seq: int             # insertion order (bigserial) — the relay publishes in this order
    event: OutboxEvent

"""Ports — the abstractions the services depend on (Dependency Inversion).

The `UnitOfWork` is the heart of the pattern: `orders` and `outbox` write
through the *same* transaction, so a business row and its event commit together
or not at all. `Broker` is the external message bus (an adapter can't be part of
the DB transaction — that's exactly why the outbox exists).
"""

from __future__ import annotations

import abc

from domain.model import Order, OutboxEvent, OutboxRecord


class Orders(abc.ABC):
    @abc.abstractmethod
    async def add(self, order: Order) -> None: ...


class Outbox(abc.ABC):
    @abc.abstractmethod
    async def add(self, event: OutboxEvent) -> None: ...

    @abc.abstractmethod
    async def fetch_unsent(self, limit: int) -> list[OutboxRecord]:
        """Unsent events in insertion order (SELECT … FOR UPDATE SKIP LOCKED)."""

    @abc.abstractmethod
    async def mark_sent(self, seqs: list[int]) -> None: ...


class UnitOfWork(abc.ABC):
    orders: Orders
    outbox: Outbox

    @abc.abstractmethod
    async def __aenter__(self) -> UnitOfWork: ...

    @abc.abstractmethod
    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None: ...

    @abc.abstractmethod
    async def commit(self) -> None: ...

    @abc.abstractmethod
    async def rollback(self) -> None: ...


class Broker(abc.ABC):
    @abc.abstractmethod
    async def publish(self, topic: str, event: OutboxEvent) -> None: ...

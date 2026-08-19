"""Ports — the abstractions the booking domain depends on (Dependency Inversion).

Explicit `abc.ABC` interfaces: an adapter must implement every abstract method
or instantiating it raises `TypeError`. The transactional invariant (never sell
one seat twice) is modeled as a **Unit of Work**: the domain opens a
transaction, row-locks the seat, and does its checks/writes inside it, while the
adapter owns BEGIN / SELECT … FOR UPDATE / COMMIT. The domain never imports
asyncpg or redis.
"""

from __future__ import annotations

import abc
from contextlib import AbstractAsyncContextManager


class SeatHoldStore(abc.ABC):
    """TTL seat holds — atomic acquire, ownership check, compare-and-delete release."""

    @abc.abstractmethod
    async def acquire(self, seat_id: str, holder: str, ttl_ms: int) -> bool: ...

    @abc.abstractmethod
    async def holder(self, seat_id: str) -> str | None: ...

    @abc.abstractmethod
    async def release(self, seat_id: str, holder: str) -> None: ...


class PaymentGateway(abc.ABC):
    """The external PSP. The stub always succeeds; the real one calls card rails."""

    @abc.abstractmethod
    async def authorize_capture(self, idempotency_key: str, seat_id: str) -> None: ...


class BookingTransaction(abc.ABC):
    """Operations available inside one booking transaction (bound to a connection)."""

    @abc.abstractmethod
    async def lock_seat(self, seat_id: str, use_lock: bool) -> str | None:
        """Return the seat status ('available'/'sold'), row-locked when use_lock; None if absent."""

    @abc.abstractmethod
    async def mark_sold(self, seat_id: str, holder: str) -> None: ...

    @abc.abstractmethod
    async def record_order(self, seat_id: str, holder: str) -> int: ...


class BookingUnitOfWork(abc.ABC):
    """Opens a transactional boundary for the confirm critical section."""

    @abc.abstractmethod
    def transaction(self) -> AbstractAsyncContextManager[BookingTransaction]: ...

"""BookingConfirmer — the critical section that prevents double-selling (C4 code element).

Orchestrates the invariant using the BookingUnitOfWork port: open a transaction,
row-lock and re-check the seat, capture payment, then mark sold and record the
order. Under concurrency the lock serialises confirms — the first commits, the
rest see 'sold' and are rejected.

`use_lock=False` drops the row lock to *demonstrate* the anomaly the lock
prevents (two confirms both read 'available' and both sell the seat).
"""

from __future__ import annotations

import asyncio

from domain.errors import SeatUnavailableError
from domain.payment_client import PaymentClient
from domain.ports import BookingUnitOfWork
from domain.seat_hold_service import SeatHoldService


class BookingConfirmer:
    def __init__(
        self,
        uow: BookingUnitOfWork,
        holds: SeatHoldService,
        payment: PaymentClient,
        race_delay: float = 0.05,
    ) -> None:
        self._uow = uow
        self._holds = holds
        self._payment = payment
        self._race_delay = race_delay  # widens the read→write window so the demo is reliable
        self.confirmed = 0
        self.rejected = 0

    async def confirm(self, seat_id: str, holder: str, payment_key: str, use_lock: bool = True) -> int:
        async with self._uow.transaction() as tx:
            status = await tx.lock_seat(seat_id, use_lock)
            if status is None:
                raise SeatUnavailableError("no such seat")
            if status != "available":
                self.rejected += 1
                raise SeatUnavailableError("seat already sold")

            # With the lock held this wait is safe (others block); without it,
            # concurrent confirms all pass the check above and race to the write.
            await asyncio.sleep(self._race_delay)

            await self._payment.capture(payment_key, seat_id)
            await tx.mark_sold(seat_id, holder)
            order_id = await tx.record_order(seat_id, holder)
            self.confirmed += 1
        await self._holds.release(seat_id, holder)
        return order_id

    def status(self) -> dict[str, int]:
        return {"confirmed": self.confirmed, "rejected": self.rejected}

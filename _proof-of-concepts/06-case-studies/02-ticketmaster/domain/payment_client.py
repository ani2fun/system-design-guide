"""PaymentClient — idempotent authorize/capture (C4 code element).

Owns the idempotency guarantee (one key per checkout attempt ⇒ one charge) and
delegates the actual PSP call to the PaymentGateway port. A retried capture with
the same key replays the first outcome instead of charging twice.
"""

from __future__ import annotations

from domain.ports import PaymentGateway


class PaymentClient:
    def __init__(self, gateway: PaymentGateway) -> None:
        self._gateway = gateway
        self._captured: set[str] = set()
        self.captures = 0
        self.replays = 0

    async def capture(self, idempotency_key: str, seat_id: str) -> None:
        if idempotency_key in self._captured:
            self.replays += 1
            return  # idempotent replay — no second charge
        await self._gateway.authorize_capture(idempotency_key, seat_id)
        self._captured.add(idempotency_key)
        self.captures += 1

    def status(self) -> dict[str, int]:
        return {"captures": self.captures, "idempotent_replays": self.replays}

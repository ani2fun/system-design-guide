"""Stub PSP adapter — the PaymentGateway port (infrastructure).

Always authorises. The idempotency guarantee lives in the domain's
PaymentClient; this stub only stands in for the external card rails.
"""

from __future__ import annotations

from domain.ports import PaymentGateway


class StubPaymentGateway(PaymentGateway):
    async def authorize_capture(self, idempotency_key: str, seat_id: str) -> None:
        return None

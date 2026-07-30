"""PaymentIntentMachine — the payment-intent state machine (C4 code element).

created → authorized → captured → settled, with refund/void branches. Illegal
transitions are impossible, not discouraged: `next_state` raises rather than
letting a payment reach a state it can't legally be in.
"""

from __future__ import annotations

from domain.errors import IllegalTransition
from domain.model import Event, State

_TRANSITIONS: dict[tuple[State, Event], State] = {
    (State.CREATED, Event.AUTHORIZE): State.AUTHORIZED,
    (State.CREATED, Event.VOID): State.VOIDED,
    (State.AUTHORIZED, Event.CAPTURE): State.CAPTURED,
    (State.AUTHORIZED, Event.VOID): State.VOIDED,
    (State.CAPTURED, Event.SETTLE): State.SETTLED,
    (State.CAPTURED, Event.REFUND): State.REFUNDED,
    (State.SETTLED, Event.REFUND): State.REFUNDED,
}


class PaymentIntentMachine:
    @staticmethod
    def next_state(state: State, event: Event) -> State:
        try:
            return _TRANSITIONS[(state, event)]
        except KeyError:
            raise IllegalTransition(f"cannot {event.value} a {state.value} payment") from None

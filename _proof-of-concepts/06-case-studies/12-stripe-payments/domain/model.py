"""Payment domain model (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class State(str, Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    SETTLED = "settled"
    REFUNDED = "refunded"
    VOIDED = "voided"


class Event(str, Enum):
    AUTHORIZE = "authorize"
    CAPTURE = "capture"
    SETTLE = "settle"
    REFUND = "refund"
    VOID = "void"


@dataclass(frozen=True, slots=True)
class Posting:
    """One leg of a double-entry transaction (positive = credit, negative = debit)."""

    account: str
    amount: int  # minor units (cents)

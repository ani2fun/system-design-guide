"""Domain model — a message (or a receipt, which is just a message going back)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Kind(str, Enum):
    MSG = "msg"
    RECEIPT = "receipt"


@dataclass(frozen=True, slots=True)
class Message:
    id: str
    sender: str
    recipient: str
    kind: Kind
    text: str = ""
    receipt_of: str | None = None   # for receipts: the message id being acknowledged
    state: str | None = None        # 'delivered' | 'read' (receipts only)

    def to_json(self) -> str:
        return json.dumps(
            {
                "id": self.id,
                "sender": self.sender,
                "recipient": self.recipient,
                "kind": self.kind.value,
                "text": self.text,
                "receipt_of": self.receipt_of,
                "state": self.state,
            }
        )

    @staticmethod
    def from_json(raw: str) -> Message:
        d: dict[str, Any] = json.loads(raw)
        return Message(
            id=str(d["id"]),
            sender=str(d["sender"]),
            recipient=str(d["recipient"]),
            kind=Kind(d["kind"]),
            text=str(d.get("text", "")),
            receipt_of=d.get("receipt_of"),
            state=d.get("state"),
        )

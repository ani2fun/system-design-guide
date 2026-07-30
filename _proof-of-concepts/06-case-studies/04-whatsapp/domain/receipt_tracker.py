"""ReceiptTracker — the sent → delivered → read ladder (C4 code element).

A receipt is just a tiny message flowing the other way. When a message is
delivered, this routes a 'delivered' receipt back to its sender; a client 'read'
event routes a 'read' receipt the same way.
"""

from __future__ import annotations

from domain.message_router import MessageRouter
from domain.model import Kind, Message


class ReceiptTracker:
    def __init__(self, router: MessageRouter) -> None:
        self._router = router
        router.set_delivery_hook(self.on_delivered)

    async def on_delivered(self, message: Message) -> None:
        await self._router.route(self._receipt(message, "delivered"))

    async def on_read(self, reader: str, sender: str, message_id: str) -> None:
        receipt = Message(
            id=f"rd-{message_id}",
            sender=reader,
            recipient=sender,
            kind=Kind.RECEIPT,
            receipt_of=message_id,
            state="read",
        )
        await self._router.route(receipt)

    @staticmethod
    def _receipt(message: Message, state: str) -> Message:
        return Message(
            id=f"{state[:1]}-{message.id}",
            sender=message.recipient,
            recipient=message.sender,
            kind=Kind.RECEIPT,
            receipt_of=message.id,
            state=state,
        )

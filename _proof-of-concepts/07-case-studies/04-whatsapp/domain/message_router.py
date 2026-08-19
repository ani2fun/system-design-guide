"""MessageRouter — inbox-first, then deliver (C4 code element).

Every message is written to the recipient's inbox *first*, then delivery is
attempted: straight to the local socket if the recipient is on this server,
otherwise published to the server that holds their socket. The inbox row is the
copy that survives when nobody is connected; it is deleted only on a delivery
ack. At-least-once — the client dedups by message id.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from domain.connection_registry import ConnectionRegistry
from domain.model import Kind, Message
from domain.ports import InboxStore, MessageBus

# A hook the ReceiptTracker registers to be told when a message was delivered.
ReceiptHook = Callable[[Message], Awaitable[None]]


class MessageRouter:
    def __init__(self, registry: ConnectionRegistry, inbox: InboxStore, bus: MessageBus) -> None:
        self._registry = registry
        self._inbox = inbox
        self._bus = bus
        self._on_delivered: ReceiptHook | None = None
        self.delivered_count = 0

    def set_delivery_hook(self, hook: ReceiptHook) -> None:
        self._on_delivered = hook

    async def route(self, message: Message) -> None:
        await self._inbox.add(message.recipient, message)  # write first
        if await self._deliver_if_local(message):
            return
        server = await self._registry.server_of(message.recipient)
        if server is not None and server != self._registry.server_id:
            await self._bus.publish(f"srv:{server}", message.to_json())
        # else the recipient is offline: the message waits in the inbox.

    async def deliver_local(self, message: Message) -> None:
        """Called by the pub/sub subscriber when a message arrives for a local socket."""
        await self._deliver_if_local(message)

    async def drain(self, user: str) -> None:
        for message in await self._inbox.drain(user):
            await self._deliver_if_local(message)

    async def _deliver_if_local(self, message: Message) -> bool:
        send = self._registry.local_sender(message.recipient)
        if send is None:
            return False
        await send(message.to_json())
        await self._inbox.ack(message.recipient, message.id)
        if message.kind is Kind.MSG and self._on_delivered is not None:
            await self._on_delivered(message)
        self.delivered_count += 1
        return True

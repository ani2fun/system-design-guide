"""Ports — the abstractions the chat-server domain depends on (Dependency Inversion).

Explicit `abc.ABC` interfaces over Redis: presence (who is online, on which
server), the per-user offline inbox, and the cross-server bus. The domain never
imports redis.
"""

from __future__ import annotations

import abc

from domain.model import Message


class PresenceStore(abc.ABC):
    """Which chat server currently holds a user's socket (or None if offline)."""

    @abc.abstractmethod
    async def set_online(self, user: str, server_id: str) -> None: ...

    @abc.abstractmethod
    async def set_offline(self, user: str) -> None: ...

    @abc.abstractmethod
    async def server_of(self, user: str) -> str | None: ...


class InboxStore(abc.ABC):
    """Per-user offline queue: written before delivery, deleted on ack, drained on reconnect."""

    @abc.abstractmethod
    async def add(self, user: str, message: Message) -> None: ...

    @abc.abstractmethod
    async def ack(self, user: str, message_id: str) -> None: ...

    @abc.abstractmethod
    async def drain(self, user: str) -> list[Message]: ...


class MessageBus(abc.ABC):
    """Cross-server delivery: publish a message to the server holding the socket."""

    @abc.abstractmethod
    async def publish(self, channel: str, payload: str) -> None: ...

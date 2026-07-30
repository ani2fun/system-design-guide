"""ConnectionRegistry — the routing table for live sockets (C4 code element).

Tracks the sockets connected to *this* chat server (in-process) and mirrors
presence to the shared PresenceStore so other servers can find a user. Every
delivery starts by asking: is the recipient here, elsewhere, or offline?
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from domain.ports import PresenceStore

Sender = Callable[[str], Awaitable[None]]  # send one JSON frame over a socket


class ConnectionRegistry:
    def __init__(self, presence: PresenceStore, server_id: str) -> None:
        self._presence = presence
        self._server_id = server_id
        self._local: dict[str, Sender] = {}

    @property
    def server_id(self) -> str:
        return self._server_id

    async def connect(self, user: str, send: Sender) -> None:
        self._local[user] = send
        await self._presence.set_online(user, self._server_id)

    async def disconnect(self, user: str) -> None:
        self._local.pop(user, None)
        await self._presence.set_offline(user)

    def local_sender(self, user: str) -> Sender | None:
        return self._local.get(user)

    async def server_of(self, user: str) -> str | None:
        return await self._presence.server_of(user)

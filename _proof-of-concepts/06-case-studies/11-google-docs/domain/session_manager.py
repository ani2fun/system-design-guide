"""SessionManager — who's in the document right now (C4 code element).

Ephemeral membership + cursor positions per document. Dies with the session;
never written to the op log.
"""

from __future__ import annotations


class SessionManager:
    def __init__(self) -> None:
        self._members: dict[str, dict[str, int]] = {}  # doc -> {user: cursor}

    def join(self, doc: str, user: str, cursor: int = 0) -> None:
        self._members.setdefault(doc, {})[user] = cursor

    def leave(self, doc: str, user: str) -> None:
        self._members.get(doc, {}).pop(user, None)

    def move_cursor(self, doc: str, user: str, pos: int) -> None:
        if user in self._members.get(doc, {}):
            self._members[doc][user] = pos

    def members(self, doc: str) -> dict[str, int]:
        return dict(self._members.get(doc, {}))

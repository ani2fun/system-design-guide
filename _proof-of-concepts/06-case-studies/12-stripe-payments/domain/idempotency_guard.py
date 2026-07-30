"""IdempotencyGuard — same key ⇒ same outcome (C4 code element).

Stores the result of the first attempt and replays it to retries. The end-to-end
duplicate suppressor a transaction alone can't provide (retries arrive as
separate requests).
"""

from __future__ import annotations

from domain.ports import PaymentTransaction


class IdempotencyGuard:
    def __init__(self, tx: PaymentTransaction) -> None:
        self._tx = tx

    async def replay(self, key: str) -> str | None:
        """Return the stored result if this key already ran, else None."""
        return await self._tx.reserve(key)

    async def remember(self, key: str, result_json: str) -> None:
        await self._tx.save_result(key, result_json)

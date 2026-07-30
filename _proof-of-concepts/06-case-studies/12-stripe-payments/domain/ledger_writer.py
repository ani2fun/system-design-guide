"""LedgerWriter — append-only double-entry postings (C4 code element).

Money is never UPDATEd; every movement is appended as postings that must sum to
zero. Balances are derived views over the entries, never a mutable field.
"""

from __future__ import annotations

from domain.errors import UnbalancedPostings
from domain.model import Posting
from domain.ports import PaymentTransaction


class LedgerWriter:
    def __init__(self, tx: PaymentTransaction) -> None:
        self._tx = tx

    async def record(self, entries: list[Posting]) -> None:
        if sum(e.amount for e in entries) != 0:
            raise UnbalancedPostings("double-entry postings must sum to zero")
        await self._tx.post(entries)

    async def balance(self, account: str) -> int:
        return await self._tx.balance(account)

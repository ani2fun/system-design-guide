"""Ports — the transactional boundary for a charge (Dependency Inversion).

The whole charge is one transaction: reserve the idempotency key, create the
payment, write the ledger, save the result. The adapter owns BEGIN/COMMIT; the
domain never imports asyncpg.
"""

from __future__ import annotations

import abc
from contextlib import AbstractAsyncContextManager

from domain.model import Posting


class PaymentTransaction(abc.ABC):
    @abc.abstractmethod
    async def reserve(self, key: str) -> str | None:
        """Reserve the idempotency key. Returns the stored result JSON if the key
        was already used (replay), else None (first time — caller does the work).
        Concurrent callers with the same key block until the first commits."""

    @abc.abstractmethod
    async def save_result(self, key: str, result_json: str) -> None: ...

    @abc.abstractmethod
    async def new_payment(self, merchant: str, amount: int, state: str) -> int:
        """Insert a payment row; return its id."""

    @abc.abstractmethod
    async def post(self, entries: list[Posting]) -> None:
        """Append double-entry ledger postings (append-only)."""

    @abc.abstractmethod
    async def balance(self, account: str) -> int: ...


class PaymentUnitOfWork(abc.ABC):
    @abc.abstractmethod
    def transaction(self) -> AbstractAsyncContextManager[PaymentTransaction]: ...

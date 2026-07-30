"""Ports — the abstractions the experiments depend on (Dependency Inversion).

`Ledger` is the database (connection factory + reset/read helpers); `Session`
is one in-flight transaction on its own connection. Both are explicit
`abc.ABC`s: an adapter that forgets a method fails at instantiation and under
mypy. The experiments know nothing about asyncpg or SQL.
"""

from __future__ import annotations

import abc


class Session(abc.ABC):
    """One transaction on its own connection. Interleave two of these to
    reproduce (or prevent) an anomaly. A locking read may block; `commit` may
    raise `SerializationConflict`."""

    @abc.abstractmethod
    async def begin(self, isolation: str) -> None:
        """BEGIN with 'READ COMMITTED' | 'REPEATABLE READ' | 'SERIALIZABLE'."""

    @abc.abstractmethod
    async def read_balance(self, account: str, *, lock: bool = False) -> int:
        """Read a balance; `lock=True` issues SELECT … FOR UPDATE."""

    @abc.abstractmethod
    async def write_balance(self, account: str, balance: int) -> None: ...

    @abc.abstractmethod
    async def count_on_call(self) -> int:
        """Count doctors currently on call (the write-skew predicate)."""

    @abc.abstractmethod
    async def set_on_call(self, doctor: str, on_call: bool) -> None: ...

    @abc.abstractmethod
    async def commit(self) -> None: ...

    @abc.abstractmethod
    async def rollback(self) -> None: ...

    @abc.abstractmethod
    async def close(self) -> None: ...


class Ledger(abc.ABC):
    @abc.abstractmethod
    async def reset_balance(self, account: str, balance: int) -> None: ...

    @abc.abstractmethod
    async def reset_on_call(self, doctors: dict[str, bool]) -> None: ...

    @abc.abstractmethod
    async def read_balance(self, account: str) -> int: ...

    @abc.abstractmethod
    async def count_on_call(self) -> int: ...

    @abc.abstractmethod
    def session(self) -> Session: ...

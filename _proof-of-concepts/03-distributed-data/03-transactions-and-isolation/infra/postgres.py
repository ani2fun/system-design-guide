"""Postgres adapters (asyncpg) implementing the ledger ports.

`PostgresSession` drives one transaction on a dedicated pooled connection using
raw BEGIN / COMMIT so the experiment controls isolation level and interleaving.
SQLSTATE 40001 is translated into the domain's `SerializationConflict`.
"""

from __future__ import annotations

import asyncpg

from domain.model import SerializationConflict
from domain.ports import Ledger, Session


def _is_serialization_error(exc: Exception) -> bool:
    return getattr(exc, "sqlstate", None) == "40001"


class PostgresSession(Session):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._con: asyncpg.Connection | None = None

    async def _conn(self) -> asyncpg.Connection:
        if self._con is None:
            self._con = await self._pool.acquire()
        return self._con

    async def begin(self, isolation: str) -> None:
        con = await self._conn()
        await con.execute(f"BEGIN ISOLATION LEVEL {isolation}")

    async def read_balance(self, account: str, *, lock: bool = False) -> int:
        con = await self._conn()
        sql = "SELECT balance FROM account WHERE name = $1" + (" FOR UPDATE" if lock else "")
        try:
            return int(await con.fetchval(sql, account))
        except asyncpg.PostgresError as exc:
            if _is_serialization_error(exc):
                raise SerializationConflict(str(exc)) from exc
            raise

    async def write_balance(self, account: str, balance: int) -> None:
        con = await self._conn()
        try:
            await con.execute("UPDATE account SET balance = $2 WHERE name = $1", account, balance)
        except asyncpg.PostgresError as exc:
            if _is_serialization_error(exc):
                raise SerializationConflict(str(exc)) from exc
            raise

    async def count_on_call(self) -> int:
        con = await self._conn()
        try:
            return int(await con.fetchval("SELECT count(*) FROM doctor WHERE on_call"))
        except asyncpg.PostgresError as exc:
            if _is_serialization_error(exc):
                raise SerializationConflict(str(exc)) from exc
            raise

    async def set_on_call(self, doctor: str, on_call: bool) -> None:
        con = await self._conn()
        try:
            await con.execute("UPDATE doctor SET on_call = $2 WHERE name = $1", doctor, on_call)
        except asyncpg.PostgresError as exc:
            if _is_serialization_error(exc):
                raise SerializationConflict(str(exc)) from exc
            raise

    async def commit(self) -> None:
        con = await self._conn()
        try:
            await con.execute("COMMIT")
        except asyncpg.PostgresError as exc:
            if _is_serialization_error(exc):
                raise SerializationConflict(str(exc)) from exc
            raise

    async def rollback(self) -> None:
        con = await self._conn()
        await con.execute("ROLLBACK")

    async def close(self) -> None:
        if self._con is not None:
            await self._pool.release(self._con)
            self._con = None


class PostgresLedger(Ledger):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PostgresLedger.connect() was not called")
        return self._pool

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=8)
        async with self._require_pool().acquire() as con:
            await con.execute(
                "CREATE TABLE IF NOT EXISTS account (name text PRIMARY KEY, balance int NOT NULL)"
            )
            await con.execute(
                "CREATE TABLE IF NOT EXISTS doctor (name text PRIMARY KEY, on_call bool NOT NULL)"
            )

    async def reset_balance(self, account: str, balance: int) -> None:
        async with self._require_pool().acquire() as con:
            await con.execute(
                "INSERT INTO account (name, balance) VALUES ($1, $2) "
                "ON CONFLICT (name) DO UPDATE SET balance = $2",
                account, balance,
            )

    async def reset_on_call(self, doctors: dict[str, bool]) -> None:
        async with self._require_pool().acquire() as con:
            await con.execute("DELETE FROM doctor")
            for name, on_call in doctors.items():
                await con.execute(
                    "INSERT INTO doctor (name, on_call) VALUES ($1, $2)", name, on_call
                )

    async def read_balance(self, account: str) -> int:
        async with self._require_pool().acquire() as con:
            return int(await con.fetchval("SELECT balance FROM account WHERE name = $1", account))

    async def count_on_call(self) -> int:
        async with self._require_pool().acquire() as con:
            return int(await con.fetchval("SELECT count(*) FROM doctor WHERE on_call"))

    def session(self) -> Session:
        return PostgresSession(self._require_pool())

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

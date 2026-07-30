"""Postgres adapter — the ExecutionStore port (infrastructure).

`claim` is the effectively-once linchpin: a conditional UPDATE that only one
concurrent worker can match. `reclaim_expired` is the redelivery: RUNNING rows
whose visibility deadline lapsed go back to PENDING.
"""

from __future__ import annotations

import asyncpg

from domain.ports import ExecutionStore


class PostgresExecutionStore(ExecutionStore):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def register(self, execution_id: str, due_ms: int) -> None:
        await self._pool.execute(
            "INSERT INTO executions (execution_id, due_ms) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            execution_id, due_ms,
        )

    async def poll_due(self, now_ms: int, window_ms: int) -> list[str]:
        rows = await self._pool.fetch(
            "SELECT execution_id FROM executions WHERE status = 'pending' AND due_ms <= $1 ORDER BY due_ms",
            now_ms + window_ms,
        )
        return [str(r["execution_id"]) for r in rows]

    async def stamp_epoch(self, execution_id: str, epoch: int) -> None:
        await self._pool.execute(
            "UPDATE executions SET epoch = $2 WHERE execution_id = $1", execution_id, epoch
        )

    async def claim(self, execution_id: str, worker: str, now_ms: int, visibility_ms: int) -> bool:
        won = await self._pool.fetchval(
            "UPDATE executions SET status = 'running', worker = $2, visibility_deadline_ms = $3 "
            "WHERE execution_id = $1 AND status = 'pending' AND due_ms <= $4 RETURNING execution_id",
            execution_id, worker, now_ms + visibility_ms, now_ms,
        )
        return won is not None

    async def heartbeat(self, execution_id: str, worker: str, now_ms: int, visibility_ms: int) -> bool:
        ok = await self._pool.fetchval(
            "UPDATE executions SET visibility_deadline_ms = $3 "
            "WHERE execution_id = $1 AND worker = $2 AND status = 'running' RETURNING execution_id",
            execution_id, worker, now_ms + visibility_ms,
        )
        return ok is not None

    async def complete(self, execution_id: str, worker: str) -> bool:
        ok = await self._pool.fetchval(
            "UPDATE executions SET status = 'completed' "
            "WHERE execution_id = $1 AND worker = $2 AND status = 'running' RETURNING execution_id",
            execution_id, worker,
        )
        return ok is not None

    async def reclaim_expired(self, now_ms: int) -> int:
        rows = await self._pool.fetch(
            "UPDATE executions SET status = 'pending', worker = NULL "
            "WHERE status = 'running' AND visibility_deadline_ms < $1 RETURNING execution_id",
            now_ms,
        )
        return len(rows)

    async def status(self, execution_id: str) -> str | None:
        value: str | None = await self._pool.fetchval(
            "SELECT status FROM executions WHERE execution_id = $1", execution_id
        )
        return value

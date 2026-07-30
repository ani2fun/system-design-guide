"""Postgres adapter — the QueryPlanner port (infrastructure).

Runs `EXPLAIN (ANALYZE, FORMAT JSON)` and digs out the decisive *scan* node so
the runner can compare plans. asyncpg is imported only here.
"""

from __future__ import annotations

import json
from typing import Any

import asyncpg

from domain.model import PlanNode
from domain.ports import QueryPlanner


def _find_scan(plan: dict[str, Any]) -> dict[str, Any] | None:
    if "Scan" in plan["Node Type"]:
        return plan
    for child in plan.get("Plans", []):
        found = _find_scan(child)
        if found is not None:
            return found
    return None


class PostgresQueryPlanner(QueryPlanner):
    def __init__(self, pool: asyncpg.Pool, table: str) -> None:
        self._pool = pool
        self._table = table

    async def explain(self, query: str) -> PlanNode:
        raw: str = await self._pool.fetchval(f"EXPLAIN (ANALYZE, FORMAT JSON) {query}")
        top: dict[str, Any] = json.loads(raw)[0]["Plan"]
        node = _find_scan(top) or top
        return PlanNode(
            node_type=str(node["Node Type"]),
            actual_ms=float(node["Actual Total Time"]),
            actual_rows=int(node["Actual Rows"]),
        )

    async def execute(self, sql: str) -> None:
        await self._pool.execute(sql)

    async def drop_secondary_indexes(self) -> None:
        rows = await self._pool.fetch(
            r"SELECT indexname FROM pg_indexes WHERE tablename = $1 AND indexname NOT LIKE '%\_pkey'",
            self._table,
        )
        for row in rows:
            await self._pool.execute(f'DROP INDEX IF EXISTS {row["indexname"]}')

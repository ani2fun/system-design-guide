"""Ports — the abstraction the runner depends on (Dependency Inversion).

`QueryPlanner` is an explicit `abc.ABC`: the Postgres adapter runs
`EXPLAIN (ANALYZE, FORMAT JSON)` and parses the decisive scan node. The runner
knows nothing about asyncpg.
"""

from __future__ import annotations

import abc

from domain.model import PlanNode


class QueryPlanner(abc.ABC):
    @abc.abstractmethod
    async def explain(self, query: str) -> PlanNode:
        """EXPLAIN ANALYZE the query; return its decisive scan node."""

    @abc.abstractmethod
    async def execute(self, sql: str) -> None:
        """Run a DDL/statement (e.g. CREATE INDEX)."""

    @abc.abstractmethod
    async def drop_secondary_indexes(self) -> None:
        """Drop every non-primary-key index on the demo table (reset to baseline)."""

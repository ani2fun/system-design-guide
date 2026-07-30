"""Domain model for the indexing walkthrough (no I/O)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Experiment:
    """One before/after comparison: run `query`, then add `index_ddl`, run again."""

    name: str
    note: str
    index_ddl: str            # the index that should change the plan
    query: str
    expect_with_index: str    # plan node we expect once the index exists


@dataclass(frozen=True, slots=True)
class PlanNode:
    """The decisive scan node from an EXPLAIN ANALYZE plan."""

    node_type: str            # 'Seq Scan' | 'Index Scan' | 'Index Only Scan' | …
    actual_ms: float
    actual_rows: int


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    experiment: Experiment
    baseline: PlanNode        # no secondary index
    indexed: PlanNode         # with the experiment's index

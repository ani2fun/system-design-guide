"""ExperimentRunner — measure a query's plan with and without an index.

For each experiment: reset to no secondary indexes, EXPLAIN the query (baseline),
create the experiment's index, EXPLAIN again. The pair of plan nodes is the
lesson made measurable.
"""

from __future__ import annotations

from domain.model import Experiment, ExperimentResult
from domain.ports import QueryPlanner


class ExperimentRunner:
    def __init__(self, planner: QueryPlanner) -> None:
        self._planner = planner

    async def run(self, experiment: Experiment) -> ExperimentResult:
        await self._planner.drop_secondary_indexes()
        baseline = await self._planner.explain(experiment.query)
        await self._planner.execute(experiment.index_ddl)
        indexed = await self._planner.explain(experiment.query)
        return ExperimentResult(experiment=experiment, baseline=baseline, indexed=indexed)

"""Smoke test: each experiment reaches its expected plan node (needs Postgres up).

    python tests/smoke.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import PG_DSN, SEED_ROWS  # noqa: E402
from app.experiments import EXPERIMENTS  # noqa: E402
from domain.runner import ExperimentRunner  # noqa: E402
from infra.db import create_pool, seed  # noqa: E402
from infra.postgres import PostgresQueryPlanner  # noqa: E402


async def main() -> None:
    pool = await create_pool(PG_DSN)
    await seed(pool, min(SEED_ROWS, 100_000))
    runner = ExperimentRunner(PostgresQueryPlanner(pool, "events"))
    for exp in EXPERIMENTS:
        result = await runner.run(exp)
        assert exp.expect_with_index in result.indexed.node_type, (
            f"{exp.name}: expected {exp.expect_with_index}, got {result.indexed.node_type}"
        )
        print(f"  ok  {exp.name}: {result.indexed.node_type}")
    await pool.close()
    print("PASS  indexing smoke")


if __name__ == "__main__":
    asyncio.run(main())

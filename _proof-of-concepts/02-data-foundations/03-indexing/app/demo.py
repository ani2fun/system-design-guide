"""Runnable indexing walkthrough — the plan before vs after each index.

    python -m app.demo   (needs Postgres up: ./run up)
"""

from __future__ import annotations

import asyncio

from app.config import PG_DSN, SEED_ROWS
from app.experiments import EXPERIMENTS
from domain.runner import ExperimentRunner
from infra.db import create_pool, seed
from infra.postgres import PostgresQueryPlanner


async def main() -> None:
    pool = await create_pool(PG_DSN)
    print(f"seeding {SEED_ROWS:,} rows into events…")
    await seed(pool, SEED_ROWS)
    runner = ExperimentRunner(PostgresQueryPlanner(pool, "events"))

    for exp in EXPERIMENTS:
        result = await runner.run(exp)
        b, i = result.baseline, result.indexed
        got = i.node_type
        ok = "✓" if exp.expect_with_index in got else "✗"
        speedup = f"{b.actual_ms / i.actual_ms:.0f}× faster" if i.actual_ms > 0 and got != b.node_type else "same plan"
        print(f"\n▶ {exp.name}: {exp.note}")
        print(f"   no index : {b.node_type:<16} {b.actual_ms:8.2f} ms")
        print(f"   +index   : {i.node_type:<16} {i.actual_ms:8.2f} ms   ({speedup})")
        print(f"   → {got}  (expected {exp.expect_with_index}) {ok}")

    await pool.close()
    print("\nPASS  indexing walkthrough")


if __name__ == "__main__":
    asyncio.run(main())

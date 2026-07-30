"""Composition root — wire the Postgres ledger into the experiments and print,
for each anomaly, the weak-isolation run (anomaly appears) beside the guarded
run (anomaly prevented).

Run: `./run` (starts Postgres) or `./run demo` (Postgres already up).
"""

from __future__ import annotations

import asyncio

from app.config import PG_DSN
from domain.experiments import LostUpdateExperiment, WriteSkewExperiment
from infra.postgres import PostgresLedger


async def main() -> None:
    ledger = PostgresLedger(PG_DSN)
    await ledger.connect()
    try:
        lost = LostUpdateExperiment(ledger)
        skew = WriteSkewExperiment(ledger)

        print("== Lost update: two read-modify-writes on one balance (start 100, "
              "expect 70) ==")
        print((await lost.run_anomaly()).render())
        print((await lost.run_fixed()).render())

        print("\n== Write skew: two on-call doctors both go off (constraint ≥1) ==")
        print((await skew.run_anomaly()).render())
        print((await skew.run_fixed()).render())

        print("\nTakeaway: weaker isolation is faster but shifts correctness onto you —")
        print("either lock the rows you read-then-write, or pay for SERIALIZABLE + retry.")
    finally:
        await ledger.close()


if __name__ == "__main__":
    asyncio.run(main())

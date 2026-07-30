"""Smoke test — assert each anomaly actually appears under weak isolation and is
actually prevented by its guard. Requires Postgres up (./run test)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import PG_DSN  # noqa: E402
from domain.experiments import LostUpdateExperiment, WriteSkewExperiment  # noqa: E402
from infra.postgres import PostgresLedger  # noqa: E402


async def main() -> None:
    ledger = PostgresLedger(PG_DSN)
    await ledger.connect()
    try:
        lost = LostUpdateExperiment(ledger)
        anomaly = await lost.run_anomaly()
        fixed = await lost.run_fixed()
        assert not anomaly.prevented and anomaly.observed == 80, anomaly
        assert fixed.prevented and fixed.observed == 70, fixed
        print("  ok  lost update: anomaly=80, FOR UPDATE fixes to 70")

        skew = WriteSkewExperiment(ledger)
        anomaly = await skew.run_anomaly()
        fixed = await skew.run_fixed()
        assert not anomaly.prevented and anomaly.observed == 0, anomaly
        assert fixed.prevented and fixed.observed == 1, fixed
        print("  ok  write skew: anomaly=0 on call, SERIALIZABLE+retry holds at 1")

        print("PASS  2 isolation experiments")
    finally:
        await ledger.close()


if __name__ == "__main__":
    asyncio.run(main())

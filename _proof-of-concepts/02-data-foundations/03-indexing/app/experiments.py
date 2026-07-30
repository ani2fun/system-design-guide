"""The indexing experiments the demo and the smoke test both run."""

from __future__ import annotations

from domain.model import Experiment

EXPERIMENTS: list[Experiment] = [
    Experiment(
        name="point lookup",
        note="WHERE email = … (unique) — the textbook Seq Scan → Index Scan",
        index_ddl="CREATE INDEX ix_email ON events (email)",
        query="SELECT * FROM events WHERE email = 'user00000042'",
        expect_with_index="Index Scan",
    ),
    Experiment(
        name="covering / index-only",
        note="SELECT a column the index INCLUDEs → no heap fetch (Index Only Scan)",
        index_ddl="CREATE INDEX ix_cov ON events (email) INCLUDE (amount)",
        query="SELECT amount FROM events WHERE email = 'user00000042'",
        expect_with_index="Index Only Scan",
    ),
    Experiment(
        name="low selectivity",
        note="WHERE status = 'ok' matches ~90% of rows — the planner keeps the Seq Scan",
        index_ddl="CREATE INDEX ix_status ON events (status)",
        query="SELECT * FROM events WHERE status = 'ok'",
        expect_with_index="Seq Scan",
    ),
]

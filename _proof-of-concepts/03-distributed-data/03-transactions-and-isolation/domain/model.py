"""Domain model — the result of one anomaly experiment, plus the one exception
the domain understands about the database (a serialization conflict).
"""

from __future__ import annotations

from dataclasses import dataclass


class SerializationConflict(Exception):
    """A transaction was aborted by the database to preserve serializability
    (Postgres SQLSTATE 40001). The application is expected to retry."""


@dataclass(frozen=True)
class AnomalyResult:
    anomaly: str          # "Lost update" / "Write skew"
    isolation: str        # the level (and guard) the run used
    observed: int         # the value the database ended up with
    expected: int         # the value a correct (serial) execution would give
    prevented: bool       # did this configuration avoid the anomaly?
    note: str             # one-line explanation

    def render(self) -> str:
        mark = "OK  prevented" if self.prevented else "XX  ANOMALY  "
        return (f"  {mark} | {self.anomaly:<12} | {self.isolation:<28} "
                f"| observed={self.observed} expected={self.expected}\n"
                f"                 └─ {self.note}")

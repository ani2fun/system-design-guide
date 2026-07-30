"""Runtime configuration for the isolation-anomalies harness."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://iso:iso@localhost:8441/iso")

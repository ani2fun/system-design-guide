"""Runtime configuration."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://ads:ads@localhost:8411/ads")
WINDOW_MS = int(os.environ.get("WINDOW_MS", "1000"))
LATENESS_MS = int(os.environ.get("LATENESS_MS", "0"))

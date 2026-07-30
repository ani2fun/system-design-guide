"""Runtime configuration, read from the environment (set by docker-compose)."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://ticket:ticket@localhost:8321/ticket")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:8322/0")
HOLD_TTL_MS = int(os.environ.get("HOLD_TTL_MS", "120000"))
RACE_DELAY = float(os.environ.get("RACE_DELAY", "0.05"))
EVENT_ID = os.environ.get("EVENT_ID", "show-1")
SEAT_COUNT = int(os.environ.get("SEAT_COUNT", "50"))

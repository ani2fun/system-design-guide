"""Runtime configuration, read from the environment (set by docker-compose)."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://shortener:shortener@localhost:8311/shortener")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:8312/0")
RANGE_BATCH = int(os.environ.get("RANGE_BATCH", "1000"))
# Start the counter high so the first codes are ~4 base62 chars, not 1.
COUNTER_START = int(os.environ.get("COUNTER_START", "1000000"))
CACHE_TTL = int(os.environ.get("CACHE_TTL", "3600"))

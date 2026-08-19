"""Runtime configuration."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://uber:uber@localhost:8382/uber")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:8381/0")

"""Runtime configuration (small TTLs so the smoke test can observe expiry)."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://js:js@localhost:8432/js")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:8431/0")
LEASE_TTL_MS = int(os.environ.get("LEASE_TTL_MS", "600"))
VISIBILITY_MS = int(os.environ.get("VISIBILITY_MS", "500"))

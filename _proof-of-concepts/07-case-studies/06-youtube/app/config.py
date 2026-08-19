"""Runtime configuration."""

import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:8371/0")

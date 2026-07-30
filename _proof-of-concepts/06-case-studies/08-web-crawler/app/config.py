"""Runtime configuration."""

import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:8391/0")
INTERVAL_MS = int(os.environ.get("INTERVAL_MS", "800"))  # per-host politeness window

# a toy robots policy: disallowed path prefixes per host
DISALLOW: dict[str, list[str]] = {"blocked.com": ["/private"]}

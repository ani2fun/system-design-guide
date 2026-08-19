"""Runtime configuration + the (cached) rule set."""

import os

from domain.model import Algorithm, Rule

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:8401/0")

# key-prefix → rule (tier/route). First match wins; DEFAULT otherwise.
RULES: list[tuple[str, Rule]] = [
    ("vip:", Rule(Algorithm.FIXED, limit=100, window_ms=1000)),
    ("free:", Rule(Algorithm.FIXED, limit=5, window_ms=1000)),
    ("bucket:", Rule(Algorithm.BUCKET, limit=3, window_ms=3000)),
    ("slide:", Rule(Algorithm.SLIDING, limit=5, window_ms=1000)),
]
DEFAULT = Rule(Algorithm.FIXED, limit=10, window_ms=1000)

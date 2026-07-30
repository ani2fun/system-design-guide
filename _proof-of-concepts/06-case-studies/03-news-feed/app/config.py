"""Shared configuration for the API and the fan-out worker (same image)."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://feed:feed@localhost:8331/feed")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:8332/0")

STREAM = os.environ.get("STREAM", "fanout")          # Redis Stream of post events
GROUP = os.environ.get("GROUP", "fanout-workers")     # consumer group

# An author with >= this many followers is a "celebrity": their posts are NOT
# fanned out on write; readers merge them in at read time. Tiny for the demo.
CELEB_THRESHOLD = int(os.environ.get("CELEB_THRESHOLD", "3"))
TIMELINE_MAX = int(os.environ.get("TIMELINE_MAX", "800"))  # cap materialized ids per user

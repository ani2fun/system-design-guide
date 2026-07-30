"""Runtime configuration for the indexing walkthrough."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://idx:idx@localhost:8341/idx")
SEED_ROWS = int(os.environ.get("SEED_ROWS", "200000"))

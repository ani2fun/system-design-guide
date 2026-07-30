"""File-service configuration."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://dbx:dbx@localhost:8361/dbx")

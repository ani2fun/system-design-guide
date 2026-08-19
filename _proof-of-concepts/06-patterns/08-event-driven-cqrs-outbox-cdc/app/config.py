"""Runtime configuration for the transactional-outbox harness."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://outbox:outbox@localhost:8451/outbox")

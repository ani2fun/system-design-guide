"""Runtime configuration."""

import os

PG_DSN = os.environ.get("PG_DSN", "postgres://pay:pay@localhost:8421/pay")

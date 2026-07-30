"""Runtime configuration (set per chat-server instance by docker-compose)."""

import os

SERVER_ID = os.environ.get("SERVER_ID", "chat1")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:8353/0")

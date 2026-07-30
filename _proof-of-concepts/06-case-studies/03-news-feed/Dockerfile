# Reproducible build with uv: deps resolved from uv.lock into /srv/.venv.
# One image runs both roles: the API (default CMD) and the worker (compose command).
FROM python:3.12-slim

# uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /srv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# install locked dependencies only (package=false → no project build)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# hexagonal layers: domain (pure) + infra (adapters) + app/worker (composition roots)
COPY domain/ ./domain/
COPY infra/ ./infra/
COPY app/ ./app/
COPY worker/ ./worker/
COPY sql/ ./sql/

ENV PATH="/srv/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Backend image. Build context: backend/ (see docker-compose.yml).

# ---- Build stage: install locked dependencies into a virtual environment ----
FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY . .

# ---- Runtime stage: no build tools, non-root user ----
FROM python:3.14-slim AS runtime

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --no-create-home app \
    && mkdir -p /data \
    && chown app:app /data

WORKDIR /app
COPY --from=build --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/roadhouse.db

USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"]

# Apply migrations, then serve.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

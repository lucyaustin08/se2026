#!/usr/bin/env bash
# Run Roadhouse for development without Docker: backend on port 8000, app on port 5173.
#
#   bash scripts/dev.sh
#
# Works in GitHub Codespaces and on any machine with uv and pnpm installed. The database is a
# SQLite file at backend/roadhouse-dev.db; delete it to start over with fresh sample data.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
# Use uv's full Python build, never a cut-down system Python (see .devcontainer).
export UV_PYTHON_PREFERENCE="${UV_PYTHON_PREFERENCE:-only-managed}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///$ROOT/backend/roadhouse-dev.db}"
export SEED_SAMPLE_DATA="${SEED_SAMPLE_DATA:-true}"

echo "==> Preparing the database"
cd "$ROOT/backend"
uv run alembic upgrade head
uv run python -m app.seed

echo "==> Generating API types for the frontend"
uv run python -m scripts.export_openapi ../frontend/openapi.json
cd "$ROOT/frontend"
pnpm gen:api

echo "==> Starting the backend on port 8000"
cd "$ROOT/backend"
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT

echo "==> Starting the app on port 5173 (press Ctrl+C to stop both)"
cd "$ROOT/frontend"
pnpm dev --host 127.0.0.1 --port 5173 --strictPort

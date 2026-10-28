#!/usr/bin/env bash
# Run Roadhouse for development without Docker: backend on port 8000, app on port 5173.
#
#   bash scripts/dev.sh
#
# Works in GitHub Codespaces, where it also starts the codespace's own PostgreSQL. Anywhere
# else, set DATABASE_URL to a PostgreSQL database you run yourself and it's used instead.
# To start over with fresh sample data in a codespace:
#   sudo runuser -u postgres -- dropdb roadhouse   (then run this script again)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
# Use uv's full Python build, never a cut-down system Python (see .devcontainer).
export UV_PYTHON_PREFERENCE="${UV_PYTHON_PREFERENCE:-only-managed}"
export SEED_SAMPLE_DATA="${SEED_SAMPLE_DATA:-true}"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "==> Starting PostgreSQL"
  bash "$ROOT/scripts/start-postgres.sh"
  export DATABASE_URL="postgresql+psycopg://roadhouse:roadhouse@localhost:5432/roadhouse"
fi

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

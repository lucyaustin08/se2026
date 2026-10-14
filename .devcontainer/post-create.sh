#!/usr/bin/env bash
# Runs once when the codespace is created: install the tools, then the locked dependencies.
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

# uv manages Python itself, so the Python version comes from backend/.python-version.
curl -LsSf https://astral.sh/uv/install.sh | sh

# pnpm comes through Corepack, at the version pinned in frontend/package.json.
corepack enable --install-directory "$HOME/.local/bin"

cd "$(dirname "$0")/.."
(cd backend && uv sync --locked)
(cd frontend && pnpm install --frozen-lockfile)

echo
echo "Ready. Start Roadhouse with:  bash scripts/dev.sh"

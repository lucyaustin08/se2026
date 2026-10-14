#!/usr/bin/env bash
# Run inside the dev container by CI: start the app the way a teammate would in a codespace,
# then check that the app page and the API (through Vite's proxy) both answer.
set -uo pipefail

bash scripts/dev.sh > /tmp/dev.log 2>&1 &

for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:5173/api/v1/members | grep -q "Jordan Avery" \
    && curl -sf http://127.0.0.1:5173/gigs | grep -q 'id="root"'; then
    echo "App and API are up."
    exit 0
  fi
  sleep 2
done

echo "The app did not start. Last lines of scripts/dev.sh output:"
tail -n 12 /tmp/dev.log
echo "--- Python diagnostics ---"
export PATH="$HOME/.local/bin:$PATH"
cd backend
uv --version
uv python find
.venv/bin/python -c "import sys; print(sys.version); print(sys.prefix, sys.base_prefix); print(sys.path)"
ls "$(.venv/bin/python -c 'import sys; print(sys.base_prefix)')/lib/python3.14" | head -5
env | grep -iE '^python|^uv_' || true
exit 1

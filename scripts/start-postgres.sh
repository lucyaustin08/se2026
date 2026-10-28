#!/usr/bin/env bash
# Start the codespace's own PostgreSQL and make sure the roadhouse user and database exist.
# scripts/dev.sh runs this; it's safe to run again. The dev container installs PostgreSQL
# (see .devcontainer/post-create.sh).
#
# The roadhouse user's password is "roadhouse". It only works on this one machine, from
# inside it, so it's fine in a development setup. Docker Compose uses its own password.
set -euo pipefail

if ! command -v pg_isready > /dev/null; then
  echo "PostgreSQL isn't installed here. In a codespace, rebuild the container"
  echo "(Command Palette: 'Codespaces: Rebuild Container'). Elsewhere, set DATABASE_URL"
  echo "to a PostgreSQL database you run yourself."
  exit 1
fi

# Run a command as the postgres user. The dev container lets us run commands as root without
# a password, but not as other users, so go through root with runuser instead of sudo -u.
as_postgres() {
  sudo runuser -u postgres -- "$@"
}

sudo service postgresql start > /dev/null
for _ in $(seq 1 30); do
  as_postgres pg_isready --quiet && break
  sleep 1
done

as_postgres psql --quiet --set ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'roadhouse') THEN
    -- CREATEDB lets the backend tests create their own roadhouse_test database.
    CREATE ROLE roadhouse LOGIN PASSWORD 'roadhouse' CREATEDB;
  END IF;
END
$$;
SQL

if ! as_postgres psql --tuples-only --no-align \
  --command "SELECT 1 FROM pg_database WHERE datname = 'roadhouse'" | grep -q 1; then
  as_postgres createdb --owner roadhouse roadhouse
fi
echo "PostgreSQL is running, with the roadhouse database."

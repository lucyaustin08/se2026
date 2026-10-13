# Roadhouse frontend

React 19, TypeScript, Vite 8 and Tailwind CSS v4, managed with pnpm.

## Running locally

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

The app is at http://localhost:5173. API calls to `/api` are proxied to the backend at http://localhost:8000, so start the backend too (see `backend/README.md`).

## API types

Request and response types come from the backend's OpenAPI schema. They are generated, not committed, so they can never drift from the backend:

```bash
pnpm gen:api:live   # with the backend running on http://localhost:8000
```

or, from `backend/`, export the schema to a file and generate from that:

```bash
uv run python -m scripts.export_openapi ../frontend/openapi.json
cd ../frontend && pnpm gen:api
```

Run one of these after pulling backend changes. CI and the Docker build generate the types themselves.

## Checks (the same ones CI runs)

```bash
pnpm gen:api   # after exporting openapi.json, see above
pnpm lint
pnpm typecheck
pnpm format:check
pnpm test:cov
```

## Without Node installed

Run any pnpm command through Docker from the repository root. On Windows Git Bash:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W)/frontend:/app" -w /app node:24-slim sh -c "corepack enable && pnpm install && pnpm test"
```

On macOS or Linux, use `"$(pwd)"` and drop `MSYS_NO_PATHCONV=1`.

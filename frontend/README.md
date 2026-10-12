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

## Checks (the same ones CI runs)

```bash
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

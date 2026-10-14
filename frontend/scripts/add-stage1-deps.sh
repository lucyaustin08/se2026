#!/bin/sh
# Adds the rest of the stack's frontend libraries (TanStack Query, openapi-fetch,
# openapi-typescript, MSW) and updates pnpm-lock.yaml. Run it inside Docker from the
# repository root:
#
#   MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W)/frontend:/app" -w /app node:24-slim sh scripts/add-stage1-deps.sh
#
# (On macOS or Linux, use "$(pwd)" instead of "$(pwd -W)" and drop MSYS_NO_PATHCONV=1.)
# Then commit frontend/package.json and frontend/pnpm-lock.yaml.
set -eu

corepack enable

pnpm add @tanstack/react-query openapi-fetch
pnpm add -D openapi-typescript msw@^2

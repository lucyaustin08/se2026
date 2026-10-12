#!/bin/sh
# One-time setup: install the frontend dependencies at their current versions and write
# pnpm-lock.yaml. Majors the project constitution fixes are pinned here; everything else
# takes the current release. Run it inside Docker from the repository root:
#
#   MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W)/frontend:/app" -w /app node:24-slim sh scripts/bootstrap-deps.sh
#
# (On macOS or Linux, use "$(pwd)" instead of "$(pwd -W)" and drop MSYS_NO_PATHCONV=1.)
# After it finishes, commit frontend/package.json and frontend/pnpm-lock.yaml.
set -eu

corepack enable
corepack use pnpm@latest

pnpm add \
  react@^19 \
  react-dom@^19 \
  react-router

pnpm add -D \
  vite@^8 \
  @vitejs/plugin-react \
  typescript@^5 \
  @types/react@^19 \
  @types/react-dom@^19 \
  @types/node@^24 \
  tailwindcss@^4 \
  @tailwindcss/vite@^4 \
  vitest@^4 \
  @vitest/coverage-v8@^4 \
  jsdom \
  @testing-library/react \
  @testing-library/user-event \
  @testing-library/jest-dom \
  @testing-library/dom \
  eslint@^9 \
  @eslint/js@^9 \
  typescript-eslint \
  eslint-plugin-react-hooks \
  globals \
  prettier

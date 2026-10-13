# Frontend image. Build context: frontend/. Extra build contexts (see docker-compose.yml):
# "infra" for nginx.conf, and "backend" to export the OpenAPI schema the API types come from.

# ---- Stage 1: export the backend's OpenAPI schema ----
FROM python:3.14-slim AS openapi
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /backend
COPY --from=backend pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY --from=backend . .
RUN .venv/bin/python -m scripts.export_openapi /openapi.json

# ---- Stage 2: install locked dependencies, generate API types, build static files ----
FROM node:24-slim AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
COPY --from=openapi /openapi.json ./openapi.json
RUN pnpm gen:api && pnpm build

# ---- Stage 3: nginx as a non-root user, serving on port 8080 ----
FROM nginxinc/nginx-unprivileged:stable-alpine AS runtime
COPY --from=infra nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1

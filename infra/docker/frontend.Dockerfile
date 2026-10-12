# Frontend image. Build context: frontend/; nginx.conf comes from the "infra" context
# (see docker-compose.yml).

# ---- Build stage: install locked dependencies and build static files ----
FROM node:24-slim AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# ---- Runtime stage: nginx as a non-root user, serving on port 8080 ----
FROM nginxinc/nginx-unprivileged:stable-alpine AS runtime
COPY --from=infra nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1

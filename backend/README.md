# Roadhouse backend

FastAPI, SQLAlchemy 2 and Alembic, managed with `uv`. The full stack and layer rules are in the project constitution.

## Layout

- `app/core/`: settings, database engine and session, domain error types
- `app/models/`: SQLAlchemy models
- `app/schemas/`: Pydantic request and response models
- `app/repositories/`: data access, no business rules
- `app/services/`: business rules, no HTTP and no SQL dialect knowledge
- `app/api/v1/`: routers, dependencies, exception handlers
- `tests/`: `test_api/`, `test_services/`, `test_repositories/`

## Running locally with uv

The app uses PostgreSQL. In a codespace, `bash scripts/dev.sh` (from the repository root) starts it and runs everything below for you. To do it by hand:

```bash
bash scripts/start-postgres.sh  # in a codespace: start PostgreSQL and create the database
cd backend
uv sync                         # create .venv and install everything from uv.lock
uv run alembic upgrade head     # apply migrations
uv run uvicorn app.main:app --reload
```

Anywhere else, run PostgreSQL yourself and set `DATABASE_URL` (see `.env.example`).

The API is at http://localhost:8000/api/v1 and interactive docs at http://localhost:8000/docs.

## Checks (the same ones CI runs)

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=app --cov-report=term-missing:skip-covered --cov-report=html --cov-fail-under=80
```

Tests need PostgreSQL running (in a codespace, `bash scripts/start-postgres.sh`). They use their own `roadhouse_test` database, which they create if it's missing and empty after every test, so they never touch your development data. Set `TEST_DATABASE_URL` to use a different one.

## Running uv through Docker

If you don't have uv installed, run any uv command in a container from the repository root. For example, to create or refresh `uv.lock`:

```bash
docker run --rm -v "${PWD}/backend:/app" -w /app ghcr.io/astral-sh/uv:python3.13-bookworm-slim uv lock
```

Docker Compose for the full app arrives in a later stage.

## Errors

Every error response uses the same envelope:

```json
{ "code": "machine_readable_snake_case", "detail": "Sentence for a human." }
```

Services raise the domain errors in `app/core/errors.py`. Only `app/api/v1/exception_handlers.py` knows their HTTP status codes:

| Error | Status |
|---|---|
| `NotFoundError` | 404 |
| `PermissionDeniedError` | 403 |
| `BusinessRuleViolation` | 409 |
| Schema validation failure | 422 |
| Anything unexpected | 500 |

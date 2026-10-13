# Roadhouse

Roadhouse is a web app that puts a band's gigs, songs, setlists and people in one place. The band manager books gigs, builds setlists and keeps everyone organized. Band members see where to be, what to play and in what key, and say when they can and can't play.

## Repository layout

- `backend/`: FastAPI, SQLAlchemy and Alembic API (Python, managed with `uv`)
- `frontend/`: React, TypeScript and Vite app (managed with `pnpm`)
- `infra/`: Dockerfiles and nginx config
- `DECISIONS.md`: every design choice that had a real alternative, and why we chose what we did

## Running the app

You need Docker Desktop running. From the repository root:

```bash
docker compose up --build
```

Then open:

- http://localhost:8080 for the app
- http://localhost:8000/docs for the interactive API docs

Stop it with `Ctrl+C`, or `docker compose down` from another terminal. Data lives in the `roadhouse-data` Docker volume, so it survives restarts. `docker compose down --volumes` wipes it.

## Developing without Docker

See `backend/README.md` and `frontend/README.md`.

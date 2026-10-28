# Roadhouse

Roadhouse is a web app that puts a band's gigs, songs, setlists and people in one place. The band manager books gigs, builds setlists and keeps everyone organized. Band members see where to be, what to play and in what key, and say when they can and can't play.

## Repository layout

- `backend/`: FastAPI, SQLAlchemy and Alembic API (Python, managed with `uv`)
- `frontend/`: React, TypeScript and Vite app (managed with `pnpm`)
- `infra/`: Dockerfiles and nginx config
- `DECISIONS.md`: every design choice that had a real alternative, and why we chose what we did

## Running the app in GitHub Codespaces (no installs needed)

Everything runs in the browser. You don't need Docker, Python or Node on your computer.

1. On the repository page on GitHub, click the green **Code** button.
2. Open the **Codespaces** tab and click **Create codespace on main** (or on your branch).
3. Wait for the setup to finish. The first time takes a few minutes, while it installs everything, including the PostgreSQL database. You'll see "Ready" in the terminal.

   An existing codespace from before the switch to PostgreSQL needs rebuilding once: open the Command Palette (`Ctrl+Shift+P`, or `Cmd+Shift+P` on a Mac) and run **Codespaces: Rebuild Container**.
4. In the terminal at the bottom, run:

   ```bash
   bash scripts/dev.sh
   ```

5. When a pop-up says the app is running on port 5173, click **Open in Browser**. If you miss it, open the **Ports** tab and click the globe icon next to "Roadhouse app".

Stop the app with `Ctrl+C`. The script starts the codespace's own PostgreSQL database each time. To start over with fresh sample data, run `sudo -u postgres dropdb roadhouse`, then run the script again.

Codespaces are free for students up to a monthly limit, through [GitHub Education](https://education.github.com). Stop your codespace when you're done (**Code → Codespaces → ⋯ → Stop codespace**) so it doesn't use up your hours.

## Running the app with Docker

You need Docker Desktop running. The first time, copy `.env.example` to `.env` in the repository root and set `POSTGRES_PASSWORD` to anything you like. Never commit `.env`. Then, from the repository root:

```bash
docker compose up --build
```

This runs three containers: the database (PostgreSQL), the backend and the frontend.

Then open:

- http://localhost:8080 for the app
- http://localhost:8000/docs for the interactive API docs

Stop it with `Ctrl+C`, or `docker compose down` from another terminal. Data lives in the `postgres-data` Docker volume, so it survives restarts. `docker compose down --volumes` wipes it.

## Developing without Docker

See `backend/README.md` and `frontend/README.md`.

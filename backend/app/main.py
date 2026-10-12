"""Application factory and the ASGI app uvicorn serves (`app.main:app`)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.exception_handlers import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import create_db_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Tests pass their own `Settings` to use a throwaway database."""
    settings = settings or get_settings()
    engine = create_db_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(title="Roadhouse API", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()

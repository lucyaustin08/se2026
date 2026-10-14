"""Shared test fixtures.

Async tests run on the anyio pytest plugin, which ships with httpx and Starlette, so no
extra test dependency is needed. Mark async test modules with `pytestmark = pytest.mark.anyio`.

Every test gets its own in-memory SQLite database with the tables created from the models.
(CI separately checks that the Alembic migrations produce the same schema.)
"""

from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app
from app.models import Base
from tests.factories import Factory


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def app() -> Iterator[FastAPI]:
    """A fresh app backed by an in-memory SQLite database with every table created."""
    application = create_app(Settings(database_url="sqlite://"))
    Base.metadata.create_all(application.state.engine)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def db(app: FastAPI) -> Iterator[Session]:
    with app.state.session_factory() as session:
        yield session


@pytest.fixture
def make(db: Session) -> Factory:
    return Factory(db)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

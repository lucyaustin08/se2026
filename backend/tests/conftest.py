"""Shared test fixtures.

Async tests run on the anyio pytest plugin, which ships with httpx and Starlette, so no
extra test dependency is needed. Mark async test modules with `pytestmark = pytest.mark.anyio`.

Tests run against PostgreSQL, the same database the app uses, at `TEST_DATABASE_URL` (by
default the `roadhouse_test` database next to the development one that scripts/dev.sh
starts). The test database is created if it's missing, its tables are built from the models
once per run, and every table is emptied, with ids starting again from 1, after each test.
(CI separately checks that the Alembic migrations produce the same schema.)
"""

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import create_db_engine
from app.main import create_app
from app.models import Base
from tests.factories import Factory

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://roadhouse:roadhouse@localhost:5432/roadhouse_test",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _create_database_if_missing(url: str) -> None:
    target = make_url(url)
    # CREATE DATABASE can't run inside a transaction, hence AUTOCOMMIT.
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": target.database},
            )
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{target.database}"'))
    finally:
        admin.dispose()


def _empty_every_table(engine: Engine) -> None:
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def database_url() -> str:
    """The test database, with fresh tables built from the models once per test run."""
    _create_database_if_missing(TEST_DATABASE_URL)
    engine = create_db_engine(TEST_DATABASE_URL)
    try:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    return TEST_DATABASE_URL


@pytest.fixture
def app(database_url: str) -> Iterator[FastAPI]:
    """A fresh app on the test database. Every table is emptied when the test ends."""
    application = create_app(Settings(database_url=database_url))
    yield application
    _empty_every_table(application.state.engine)
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

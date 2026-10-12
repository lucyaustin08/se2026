"""Shared test fixtures.

Async tests run on the anyio pytest plugin, which ships with httpx and Starlette, so no
extra test dependency is needed. Mark async test modules with `pytestmark = pytest.mark.anyio`.
"""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def app() -> FastAPI:
    """A fresh app backed by an in-memory SQLite database."""
    return create_app(Settings(database_url="sqlite://"))


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

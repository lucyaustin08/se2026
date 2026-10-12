"""Database engine and session factory.

Sessions are synchronous by design: FastAPI runs sync dependencies and routes in its
threadpool, which is correct at this scale and much easier to test than an async engine.
"""

from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

_IN_MEMORY_SQLITE_URLS = {"sqlite://", "sqlite:///:memory:"}


def create_db_engine(database_url: str) -> Engine:
    """Create an engine for `database_url`, applying SQLite-specific settings when needed."""
    if database_url in _IN_MEMORY_SQLITE_URLS:
        # One shared connection, or each new connection would see an empty database.
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    elif database_url.startswith("sqlite"):
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(database_url)

    if engine.dialect.name == "sqlite":
        _enable_sqlite_foreign_keys(engine)
    return engine


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    """SQLite ignores foreign key constraints unless each connection turns them on."""

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the factory the API uses to open one session per request."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

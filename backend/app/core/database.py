"""Database engine and session factory (PostgreSQL).

Sessions are synchronous by design: FastAPI runs sync dependencies and routes in its
threadpool, which is correct at this scale and much easier to test than an async engine.
"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(database_url: str) -> Engine:
    """Create an engine for a PostgreSQL `database_url` (`postgresql+psycopg://...`).

    Every connection works in UTC, so PostgreSQL hands back times the same way whatever
    time zone its server runs in. Converting to the band's local time happens explicitly,
    where a rule needs it.
    """
    return create_engine(
        database_url,
        connect_args={"options": "-c timezone=UTC"},
        # Check a pooled connection still works before using it, so a restarted database
        # doesn't fail the next request.
        pool_pre_ping=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the factory the API uses to open one session per request."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

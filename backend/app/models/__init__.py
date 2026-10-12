"""SQLAlchemy models. Import every model module here so Alembic can see it."""

from app.models.base import Base

__all__ = ["Base"]

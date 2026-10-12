"""Application settings, read from environment variables."""

import os
from dataclasses import dataclass

DEFAULT_DATABASE_URL = "sqlite:///./roadhouse.db"


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration. Build one with `get_settings()` or directly in tests."""

    database_url: str


def get_settings() -> Settings:
    """Read settings from the environment, falling back to local-development defaults."""
    return Settings(database_url=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))

"""Application settings, read from environment variables."""

import os
from dataclasses import dataclass

# The local development database that scripts/dev.sh starts in a codespace. Its password is
# only ever used on that one machine; Docker Compose and anything shared set DATABASE_URL.
DEFAULT_DATABASE_URL = "postgresql+psycopg://roadhouse:roadhouse@localhost:5432/roadhouse"

# Everyone in the band is in one time zone (DECISIONS.md, "Gig times entered in the browser's
# local time"). Rules that need the band's local calendar, such as recurring busy times, use it.
BAND_TIME_ZONE_NAME = "America/New_York"


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration. Build one with `get_settings()` or directly in tests."""

    database_url: str


def get_settings() -> Settings:
    """Read settings from the environment, falling back to local-development defaults."""
    return Settings(database_url=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))

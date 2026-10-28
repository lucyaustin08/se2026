"""The band's own time zone.

Times are stored and sent in UTC. A few rules need the band's local calendar instead, such
as "on the same day as a gig". Everyone in the band is in one time zone (see DECISIONS.md,
"Gig times entered in the browser's local time"), so it's a single constant.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

BAND_TIME_ZONE = ZoneInfo("America/New_York")


def band_date(moment: datetime) -> date:
    """The calendar date at the band's location for a timezone-aware moment."""
    return moment.astimezone(BAND_TIME_ZONE).date()

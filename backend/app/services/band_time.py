"""The band's own time zone.

Times are stored and sent in UTC. A few rules need the band's local calendar instead, such
as "on the same day as a gig". Everyone in the band is in one time zone (see DECISIONS.md,
"Gig times entered in the browser's local time"), so it's a single constant.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import BAND_TIME_ZONE_NAME

BAND_TIME_ZONE = ZoneInfo(BAND_TIME_ZONE_NAME)


def band_date(moment: datetime) -> date:
    """The calendar date at the band's location for a timezone-aware moment."""
    return moment.astimezone(BAND_TIME_ZONE).date()


def describe_moment(moment: datetime) -> str:
    """Like "Mon, Nov 2 at 8:00 PM", in the band's time zone."""
    local = moment.astimezone(BAND_TIME_ZONE)
    hour = local.strftime("%I").lstrip("0")
    return f"{local:%a, %b} {local.day} at {hour}:{local:%M %p}"

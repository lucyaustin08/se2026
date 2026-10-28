"""When members can't play."""

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, SmallInteger, String, Time
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import BAND_TIME_ZONE_NAME
from app.models.base import Base
from app.models.types import UTCDateTime, utcnow

if TYPE_CHECKING:
    from app.models.member import Member


class BusyTime(Base):
    """A one-off stretch of time when a member is busy. It may run over several days."""

    __tablename__ = "busy_times"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    member: Mapped["Member"] = relationship(lazy="joined")


class RecurringBusyTime(Base):
    """A weekly rule, such as "weekdays, 8:00 AM to 5:00 PM", from one date to another.

    A repeating clock time isn't one moment, so it's stored as the rule itself: local clock
    times plus the time zone they're in. PostgreSQL turns it into real moments for each date
    when it's needed (see `RecurringBusyTimeRepository.occurrences`), so 8:00 AM stays 8:00 AM
    across daylight saving changes. An end time at or before the start time means the busy
    time runs past midnight into the next day.
    """

    __tablename__ = "recurring_busy_times"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    # ISO weekday numbers, as PostgreSQL's ISODOW gives them: 1 is Monday, 7 is Sunday.
    weekdays: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger))
    start_time: Mapped[time] = mapped_column(Time())
    end_time: Mapped[time] = mapped_column(Time())
    # The first date it can apply, and the last (inclusive). No last date means it keeps going.
    starts_on: Mapped[date]
    ends_on: Mapped[date | None]
    time_zone: Mapped[str] = mapped_column(String(64), default=BAND_TIME_ZONE_NAME)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    member: Mapped["Member"] = relationship(lazy="joined")

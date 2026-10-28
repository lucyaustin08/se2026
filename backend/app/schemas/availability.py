"""Request and response models for busy times and gig availability."""

from datetime import date, datetime, time
from enum import StrEnum
from typing import Annotated, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import Role
from app.schemas.gigs import UtcDatetime
from app.schemas.members import MemberSummary
from app.schemas.pagination import Page


class BusyTimeSort(StrEnum):
    STARTS_AT = "starts_at"
    STARTS_AT_DESC = "-starts_at"


class BusyTimeIn(BaseModel):
    """A one-off busy time. Used to add one, and to change one (both times are sent)."""

    model_config = ConfigDict(extra="forbid")

    starts_at: UtcDatetime
    ends_at: UtcDatetime

    @model_validator(mode="after")
    def _ends_after_it_starts(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise ValueError("the end has to be after the start")
        return self


class BusyTimeOut(BaseModel):
    id: int
    member: MemberSummary
    starts_at: datetime
    ends_at: datetime
    created_at: datetime


class BusyTimePage(Page[BusyTimeOut]):
    pass


class ConflictKind(StrEnum):
    """Why a player is busy during a gig."""

    BUSY_TIME = "busy_time"
    WEEKLY_BUSY_TIME = "weekly_busy_time"
    GIG = "gig"


class Conflict(BaseModel):
    kind: ConflictKind
    starts_at: datetime
    ends_at: datetime
    # Filled in for another gig the player has accepted.
    gig_id: int | None
    venue_name: str | None


class PlayerAvailability(BaseModel):
    member: MemberSummary
    primary_role: Role | None
    secondary_role: Role | None
    busy: bool
    conflicts: list[Conflict]


class GigAvailability(BaseModel):
    """Who can play a gig: everyone but the manager, checked from soundcheck to the end.

    For a gig with no date yet, the window is `null` and nobody is marked busy.
    """

    window_starts_at: datetime | None
    window_ends_at: datetime | None
    players: list[PlayerAvailability]


# ---- Recurring (weekly) busy times -------------------------------------------------------------

# ISO weekday numbers: 1 is Monday, 7 is Sunday.
Weekday = Annotated[int, Field(ge=1, le=7)]


class RecurringBusyTimeSort(StrEnum):
    STARTS_ON = "starts_on"
    STARTS_ON_DESC = "-starts_on"


class RecurringBusyTimeIn(BaseModel):
    """A weekly busy time, in the band's local clock time. Used to add one and to change one
    (every field is sent again).

    An `end_time` at or before `start_time` means it runs past midnight into the next day, so
    the two can't be equal. `ends_on` is the last date it can start on; leave it out to keep it
    going until it's changed.
    """

    model_config = ConfigDict(extra="forbid")

    weekdays: Annotated[list[Weekday], Field(min_length=1, max_length=7)]
    start_time: time
    end_time: time
    starts_on: date
    ends_on: date | None = None

    @field_validator("weekdays")
    @classmethod
    def _each_day_once_in_order(cls, weekdays: list[int]) -> list[int]:
        return sorted(set(weekdays))

    @model_validator(mode="after")
    def _times_and_dates_make_sense(self) -> Self:
        if self.end_time == self.start_time:
            raise ValueError("the end time has to be different from the start time")
        if self.ends_on is not None and self.ends_on < self.starts_on:
            raise ValueError("the last date can't be before the first date")
        return self


class RecurringBusyTimeOut(BaseModel):
    id: int
    member: MemberSummary
    weekdays: list[int]
    start_time: time
    end_time: time
    starts_on: date
    ends_on: date | None
    time_zone: str
    created_at: datetime


class RecurringBusyTimePage(Page[RecurringBusyTimeOut]):
    pass


# ---- Every busy period in a date range, for the calendar ----------------------------------------

# The calendar's month view shows up to six weeks; this leaves room around it.
MAX_CALENDAR_DAYS = 62


class BusyPeriodKind(StrEnum):
    ONE_OFF = "one_off"
    WEEKLY = "weekly"


class BusyPeriod(BaseModel):
    """One stretch of busy time: a one-off busy time, or one day's occurrence of a weekly one."""

    kind: BusyPeriodKind
    # The busy time's id, or the weekly rule's id.
    source_id: int
    member: MemberSummary
    starts_at: datetime
    ends_at: datetime


class BusyPeriodsQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starts_before: AwareDatetime
    ends_after: AwareDatetime

    @model_validator(mode="after")
    def _a_calendar_sized_range(self) -> Self:
        days = (self.starts_before - self.ends_after).total_seconds() / 86_400
        if days <= 0:
            raise ValueError("starts_before has to be after ends_after")
        if days > MAX_CALENDAR_DAYS:
            raise ValueError(f"ask for at most {MAX_CALENDAR_DAYS} days at a time")
        return self


class BusyPeriods(BaseModel):
    """Every busy period that overlaps the range, earliest first. Not paged: the range is
    limited to a calendar's worth of days instead."""

    ends_after: datetime
    starts_before: datetime
    periods: list[BusyPeriod]

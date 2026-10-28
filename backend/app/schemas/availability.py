"""Request and response models for busy times and gig availability."""

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

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

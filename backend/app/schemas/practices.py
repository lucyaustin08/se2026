"""Request and response models for practices."""

from datetime import date, datetime, time
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import InvitationStatus
from app.models.practice import DEFAULT_PRACTICE_MINUTES
from app.schemas.gigs import Name, Notes, UtcDatetime
from app.schemas.members import MemberSummary
from app.schemas.pagination import Page

# At least half an hour, at most a long day.
MIN_PRACTICE_MINUTES = 30
MAX_PRACTICE_MINUTES = 720
PracticeMinutes = Annotated[int, Field(ge=MIN_PRACTICE_MINUTES, le=MAX_PRACTICE_MINUTES)]
MAX_INVITEES = 20


class PracticeSort(StrEnum):
    STARTS_AT = "starts_at"
    STARTS_AT_DESC = "-starts_at"


class PracticeCreate(BaseModel):
    """A one-time practice and who's invited.

    `confirm_same_day` says the scheduler has seen the warning that a gig is on the same day
    and wants the practice anyway. Without it, a same-day practice is refused with a `409`.
    """

    model_config = ConfigDict(extra="forbid")

    starts_at: UtcDatetime
    length_minutes: PracticeMinutes = DEFAULT_PRACTICE_MINUTES
    location: Name | None = None
    notes: Notes | None = None
    member_ids: Annotated[list[int], Field(min_length=1, max_length=MAX_INVITEES)]
    confirm_same_day: bool = False


class PracticeInvitationOut(BaseModel):
    member: MemberSummary
    status: InvitationStatus
    responded_at: datetime | None


class PracticeOut(BaseModel):
    id: int
    starts_at: datetime
    ends_at: datetime
    length_minutes: int
    location: str | None
    notes: str | None
    scheduled_by: MemberSummary
    invitations: list[PracticeInvitationOut]
    # The acting member's own answer, or null if they aren't invited.
    my_status: InvitationStatus | None
    created_at: datetime


class PracticePage(Page[PracticeOut]):
    pass


class SuggestedTime(BaseModel):
    """One possible practice time, with who could and couldn't come."""

    starts_at: datetime
    ends_at: datetime
    available: list[MemberSummary]
    unavailable: list[MemberSummary]
    # A gig on the same local day, if there is one. Suggestions never overlap a gig.
    same_day_gig: str | None


class PracticeSuggestions(BaseModel):
    """The best time on each day searched, best days first."""

    searched_from: date
    searched_to: date
    suggestions: list[SuggestedTime]


class PracticeSuggestionQuery(BaseModel):
    """What to search for: who's invited, how long, and the hours of the day to consider."""

    model_config = ConfigDict(extra="forbid")

    member_ids: Annotated[list[int], Field(min_length=1, max_length=MAX_INVITEES)]
    length_minutes: PracticeMinutes = DEFAULT_PRACTICE_MINUTES
    earliest: time = time(17, 0)
    latest: time = time(23, 0)

    @model_validator(mode="after")
    def _the_practice_fits_in_the_hours(self) -> Self:
        earliest = self.earliest.hour * 60 + self.earliest.minute
        latest = self.latest.hour * 60 + self.latest.minute
        if latest - earliest < self.length_minutes:
            raise ValueError("the hours to search are shorter than the practice")
        return self

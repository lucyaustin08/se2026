"""Request and response models for practices."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InvitationStatus
from app.models.practice import DEFAULT_PRACTICE_MINUTES
from app.schemas.gigs import Name, Notes, UtcDatetime
from app.schemas.members import MemberSummary
from app.schemas.pagination import Page

# At least half an hour, at most a long day.
PracticeMinutes = Annotated[int, Field(ge=30, le=720)]
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

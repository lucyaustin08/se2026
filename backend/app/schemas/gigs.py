"""Request and response models for gigs.

Input and output contacts are separate classes on purpose: a model with defaults would make
FastAPI publish two OpenAPI schemas (`Contact-Input` and `Contact-Output`) for one name.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import GigStatus, GigType, Role
from app.models.gig import DEFAULT_LOAD_IN_OFFSET_MINUTES, DEFAULT_SOUNDCHECK_OFFSET_MINUTES
from app.schemas.members import MemberSummary
from app.schemas.pagination import Page

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]
OffsetMinutes = Annotated[int, Field(ge=0, le=720)]
PayCents = Annotated[int, Field(ge=0, le=100_000_000)]


class GigSort(StrEnum):
    FIRST_SET_AT = "first_set_at"
    FIRST_SET_AT_DESC = "-first_set_at"
    CREATED_AT = "created_at"
    CREATED_AT_DESC = "-created_at"
    VENUE_NAME = "venue_name"
    VENUE_NAME_DESC = "-venue_name"


class ContactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    phone: Phone | None = None
    email: Email | None = None


class LineupAssignmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: Role
    member_id: int


class GigCreate(BaseModel):
    """A new gig. It is always saved as potential, and every field may be left empty."""

    model_config = ConfigDict(extra="forbid")

    first_set_at: AwareDatetime | None = None
    load_in_offset_minutes: OffsetMinutes = DEFAULT_LOAD_IN_OFFSET_MINUTES
    soundcheck_offset_minutes: OffsetMinutes = DEFAULT_SOUNDCHECK_OFFSET_MINUTES
    venue_name: Name | None = None
    venue_address: Address | None = None
    gig_type: GigType | None = None
    pay_cents: PayCents | None = None
    venue_contact: ContactIn | None = None
    booking_contact: ContactIn | None = None


class GigUpdate(BaseModel):
    """A partial update. Omitted fields are unchanged; `null` clears a field.

    A `null` offset resets it to its default. `lineup`, when present, replaces the whole lineup.
    """

    model_config = ConfigDict(extra="forbid")

    first_set_at: AwareDatetime | None = None
    load_in_offset_minutes: OffsetMinutes | None = None
    soundcheck_offset_minutes: OffsetMinutes | None = None
    venue_name: Name | None = None
    venue_address: Address | None = None
    gig_type: GigType | None = None
    pay_cents: PayCents | None = None
    venue_contact: ContactIn | None = None
    booking_contact: ContactIn | None = None
    lineup: list[LineupAssignmentIn] | None = None


class ContactOut(BaseModel):
    name: str | None
    phone: str | None
    email: str | None


class LineupSlotOut(BaseModel):
    slot: Role
    member: MemberSummary | None


class GigDetail(BaseModel):
    id: int
    status: GigStatus
    first_set_at: datetime | None
    load_in_at: datetime | None
    soundcheck_at: datetime | None
    load_in_offset_minutes: int
    soundcheck_offset_minutes: int
    venue_name: str | None
    venue_address: str | None
    gig_type: GigType | None
    pay_cents: int | None
    venue_contact: ContactOut | None
    booking_contact: ContactOut | None
    lineup: list[LineupSlotOut]
    missing_for_booking: list[str]
    created_at: datetime


class GigListItem(BaseModel):
    """One row of the gig list. `restricted` rows show only the date, with no details."""

    id: int
    status: GigStatus
    first_set_at: datetime | None
    venue_name: str | None
    gig_type: GigType | None
    restricted: bool


class GigPage(Page[GigListItem]):
    pass

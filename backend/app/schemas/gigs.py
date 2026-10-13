"""Request and response models for gigs.

Input and output models are separate classes on purpose: a model with defaults would make
FastAPI publish two OpenAPI schemas (`X-Input` and `X-Output`) for one name.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models.enums import ContactLabel, GigStatus, LineupSize, Role, SlotStatus
from app.models.gig import (
    DEFAULT_LOAD_IN_OFFSET_MINUTES,
    DEFAULT_PERFORMANCE_MINUTES,
    DEFAULT_SOUNDCHECK_OFFSET_MINUTES,
)
from app.schemas.members import MemberSummary
from app.schemas.pagination import Page

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
# Any time zone is accepted on input, and it's converted to UTC immediately, so responses
# and the database only ever see UTC.
UtcDatetime = Annotated[AwareDatetime, AfterValidator(lambda value: value.astimezone(UTC))]
OffsetMinutes = Annotated[int, Field(ge=0, le=720)]
PerformanceMinutes = Annotated[int, Field(ge=15, le=720)]
PayCents = Annotated[int, Field(ge=0, le=100_000_000)]

MAX_CONTACTS = 20


def _unique_roles(roles: list[Role]) -> list[Role]:
    if len(set(roles)) != len(roles):
        raise ValueError("each role can appear only once")
    return roles


Roles = Annotated[list[Role], AfterValidator(_unique_roles)]


class GigSort(StrEnum):
    FIRST_SET_AT = "first_set_at"
    FIRST_SET_AT_DESC = "-first_set_at"
    CREATED_AT = "created_at"
    CREATED_AT_DESC = "-created_at"
    VENUE_NAME = "venue_name"
    VENUE_NAME_DESC = "-venue_name"


# ---- Requests ------------------------------------------------------------------------------


class ContactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: ContactLabel = ContactLabel.VENUE
    name: Name | None = None
    phone: Phone | None = None
    email: Email | None = None
    notes: Notes | None = None

    @model_validator(mode="after")
    def _not_empty(self) -> Self:
        if not (self.name or self.phone or self.email or self.notes):
            raise ValueError("a contact needs at least a name, phone, email or notes")
        return self


Contacts = Annotated[list[ContactIn], Field(max_length=MAX_CONTACTS)]


class GigCreate(BaseModel):
    """A new gig. It is always saved as potential, and every field may be left empty."""

    model_config = ConfigDict(extra="forbid")

    first_set_at: UtcDatetime | None = None
    load_in_offset_minutes: OffsetMinutes = DEFAULT_LOAD_IN_OFFSET_MINUTES
    soundcheck_offset_minutes: OffsetMinutes = DEFAULT_SOUNDCHECK_OFFSET_MINUTES
    performance_minutes: PerformanceMinutes = DEFAULT_PERFORMANCE_MINUTES
    venue_name: Name | None = None
    venue_address: Address | None = None
    pay_cents: PayCents | None = None
    roles: Roles = Field(default_factory=list)
    contacts: Contacts = Field(default_factory=list)


class GigUpdate(BaseModel):
    """A partial update. Omitted fields are unchanged; `null` clears a field.

    A `null` time length resets it to its default. `roles` and `contacts`, when present,
    replace the whole list. Slots for roles that stay keep their invitations.
    """

    model_config = ConfigDict(extra="forbid")

    first_set_at: UtcDatetime | None = None
    load_in_offset_minutes: OffsetMinutes | None = None
    soundcheck_offset_minutes: OffsetMinutes | None = None
    performance_minutes: PerformanceMinutes | None = None
    venue_name: Name | None = None
    venue_address: Address | None = None
    pay_cents: PayCents | None = None
    roles: Roles | None = None
    contacts: Contacts | None = None


class InvitationIn(BaseModel):
    """Invite a member to fill a slot, with what the band leader decided to pay them."""

    model_config = ConfigDict(extra="forbid")

    member_id: int
    pay_cents: PayCents | None = None


class SlotPayIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pay_cents: PayCents | None


# ---- Responses -----------------------------------------------------------------------------


class ContactOut(BaseModel):
    id: int
    label: ContactLabel
    name: str | None
    phone: str | None
    email: str | None
    notes: str | None


class SlotOut(BaseModel):
    id: int
    role: Role
    status: SlotStatus
    member: MemberSummary | None
    pay_cents: int | None
    responded_at: datetime | None


class GigDetail(BaseModel):
    id: int
    status: GigStatus
    first_set_at: datetime | None
    load_in_at: datetime | None
    soundcheck_at: datetime | None
    end_at: datetime | None
    load_in_offset_minutes: int
    soundcheck_offset_minutes: int
    performance_minutes: int
    venue_name: str | None
    venue_address: str | None
    lineup_size: LineupSize | None
    pay_cents: int | None
    slots: list[SlotOut]
    contacts: list[ContactOut]
    my_slot_id: int | None
    missing_for_booking: list[str]
    created_at: datetime


class GigListItem(BaseModel):
    """One row of the gig list. `restricted` rows show only the date, with no details."""

    id: int
    status: GigStatus
    first_set_at: datetime | None
    venue_name: str | None
    lineup_size: LineupSize | None
    restricted: bool
    my_slot_status: SlotStatus | None


class GigPage(Page[GigListItem]):
    pass

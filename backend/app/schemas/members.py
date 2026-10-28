from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.models.enums import Role
from app.schemas.fields import Email, Phone
from app.schemas.pagination import Page

MemberName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class MemberSort(StrEnum):
    NAME = "name"
    NAME_DESC = "-name"


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    primary_role: Role | None
    is_manager: bool
    is_band_leader: bool


class MemberSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MemberPage(Page[MemberRead]):
    pass


class MemberProfile(BaseModel):
    """A member's profile.

    `email` and `phone` are `null` unless the reader is that member, the manager or the band
    leader. The role flags are shown, but nobody can change them.
    """

    id: int
    name: str
    email: str | None
    phone: str | None
    primary_role: Role | None
    secondary_role: Role | None
    is_manager: bool
    is_band_leader: bool


class MemberProfileUpdate(BaseModel):
    """A member editing their own profile. Omitted fields are unchanged.

    `null` clears the phone or an instrument. Name and email can't be cleared. Role fields
    aren't accepted at all: sending one is a validation error, because roles are fixed.
    """

    model_config = ConfigDict(extra="forbid")

    name: MemberName | None = None
    email: Email | None = None
    phone: Phone | None = None
    primary_role: Role | None = None
    secondary_role: Role | None = None

    @model_validator(mode="after")
    def _name_and_email_stay_set(self) -> Self:
        for field in ("name", "email"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} can't be empty")
        return self

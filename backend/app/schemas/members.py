from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.models.enums import Role
from app.schemas.pagination import Page


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

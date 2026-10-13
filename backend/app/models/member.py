from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import Role
from app.models.types import UTCDateTime, str_enum, utcnow


class Member(Base):
    """A person in the band. The manager is also a member, with `is_manager` set."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    primary_role: Mapped[Role | None] = mapped_column(str_enum(Role, "member_role"))
    is_manager: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

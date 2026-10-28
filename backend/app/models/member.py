from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import Role
from app.models.types import UTCDateTime, str_enum, utcnow


class Member(Base):
    """A person in the band.

    The manager organizes gigs and doesn't play (`is_manager`). The band leader plays, and
    every gig needs them in the lineup (`is_band_leader`).
    """

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    primary_role: Mapped[Role | None] = mapped_column(str_enum(Role, "member_role"))
    # A second instrument the member can cover. Never the same as the primary role.
    secondary_role: Mapped[Role | None] = mapped_column(str_enum(Role, "member_secondary_role"))
    phone: Mapped[str | None] = mapped_column(String(40))
    is_manager: Mapped[bool] = mapped_column(default=False)
    is_band_leader: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

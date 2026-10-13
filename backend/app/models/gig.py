from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import GigStatus, GigType, Role
from app.models.types import UTCDateTime, str_enum, utcnow

if TYPE_CHECKING:
    from app.models.member import Member

DEFAULT_LOAD_IN_OFFSET_MINUTES = 120
DEFAULT_SOUNDCHECK_OFFSET_MINUTES = 60


class Gig(Base):
    __tablename__ = "gigs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[GigStatus] = mapped_column(
        str_enum(GigStatus, "gig_status"), default=GigStatus.POTENTIAL
    )

    # Load-in and soundcheck are stored as minutes before the first set, so moving the
    # first set moves them too. Their clock times are computed (see the properties below).
    first_set_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
    load_in_offset_minutes: Mapped[int] = mapped_column(default=DEFAULT_LOAD_IN_OFFSET_MINUTES)
    soundcheck_offset_minutes: Mapped[int] = mapped_column(
        default=DEFAULT_SOUNDCHECK_OFFSET_MINUTES
    )

    venue_name: Mapped[str | None] = mapped_column(String(200))
    venue_address: Mapped[str | None] = mapped_column(String(300))
    gig_type: Mapped[GigType | None] = mapped_column(str_enum(GigType, "gig_type"))
    pay_cents: Mapped[int | None]

    venue_contact_name: Mapped[str | None] = mapped_column(String(200))
    venue_contact_phone: Mapped[str | None] = mapped_column(String(40))
    venue_contact_email: Mapped[str | None] = mapped_column(String(254))
    booking_contact_name: Mapped[str | None] = mapped_column(String(200))
    booking_contact_phone: Mapped[str | None] = mapped_column(String(40))
    booking_contact_email: Mapped[str | None] = mapped_column(String(254))

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    assignments: Mapped[list["GigAssignment"]] = relationship(
        back_populates="gig",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="GigAssignment.id",
    )

    @property
    def load_in_at(self) -> datetime | None:
        if self.first_set_at is None:
            return None
        return self.first_set_at - timedelta(minutes=self.load_in_offset_minutes)

    @property
    def soundcheck_at(self) -> datetime | None:
        if self.first_set_at is None:
            return None
        return self.first_set_at - timedelta(minutes=self.soundcheck_offset_minutes)

    def is_assigned(self, member_id: int) -> bool:
        return any(assignment.member_id == member_id for assignment in self.assignments)


class GigAssignment(Base):
    """One filled lineup slot: which member plays which role at a gig."""

    __tablename__ = "gig_assignments"
    __table_args__ = (
        UniqueConstraint("gig_id", "slot"),
        UniqueConstraint("gig_id", "member_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    gig_id: Mapped[int] = mapped_column(ForeignKey("gigs.id", ondelete="CASCADE"))
    slot: Mapped[Role] = mapped_column(str_enum(Role, "lineup_slot"))
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    gig: Mapped[Gig] = relationship(back_populates="assignments")
    member: Mapped["Member"] = relationship(lazy="joined")

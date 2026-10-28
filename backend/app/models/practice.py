"""Band practices and who is invited to them."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import InvitationStatus
from app.models.types import UTCDateTime, str_enum, utcnow

if TYPE_CHECKING:
    from app.models.member import Member

DEFAULT_PRACTICE_MINUTES = 180


class Practice(Base):
    """A one-time practice. Its end is computed from the start and length, never stored."""

    __tablename__ = "practices"

    id: Mapped[int] = mapped_column(primary_key=True)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    length_minutes: Mapped[int] = mapped_column(default=DEFAULT_PRACTICE_MINUTES)
    location: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(1000))
    scheduled_by_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    scheduled_by: Mapped["Member"] = relationship(lazy="joined")
    invitations: Mapped[list["PracticeInvitation"]] = relationship(
        back_populates="practice",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PracticeInvitation.id",
    )

    @property
    def ends_at(self) -> datetime:
        return self.starts_at + timedelta(minutes=self.length_minutes)

    def invitation_for(self, member_id: int) -> "PracticeInvitation | None":
        return next((i for i in self.invitations if i.member_id == member_id), None)


class PracticeInvitation(Base):
    __tablename__ = "practice_invitations"
    __table_args__ = (UniqueConstraint("practice_id", "member_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    practice_id: Mapped[int] = mapped_column(ForeignKey("practices.id", ondelete="CASCADE"))
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    status: Mapped[InvitationStatus] = mapped_column(
        str_enum(InvitationStatus, "invitation_status"), default=InvitationStatus.INVITED
    )
    responded_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    practice: Mapped[Practice] = relationship(back_populates="invitations")
    member: Mapped["Member"] = relationship(lazy="joined")

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ContactLabel, GigStatus, Role, SlotStatus
from app.models.types import UTCDateTime, str_enum, utcnow

if TYPE_CHECKING:
    from app.models.member import Member

DEFAULT_LOAD_IN_OFFSET_MINUTES = 120
DEFAULT_SOUNDCHECK_OFFSET_MINUTES = 60
DEFAULT_PERFORMANCE_MINUTES = 180


class Gig(Base):
    __tablename__ = "gigs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[GigStatus] = mapped_column(
        str_enum(GigStatus, "gig_status"), default=GigStatus.POTENTIAL
    )

    # Only the first set is stored as a time. Load-in and soundcheck are minutes before it,
    # and the end is minutes after it, so moving the first set moves all of them. Their
    # clock times are computed (see the properties below).
    first_set_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
    load_in_offset_minutes: Mapped[int] = mapped_column(default=DEFAULT_LOAD_IN_OFFSET_MINUTES)
    soundcheck_offset_minutes: Mapped[int] = mapped_column(
        default=DEFAULT_SOUNDCHECK_OFFSET_MINUTES
    )
    performance_minutes: Mapped[int] = mapped_column(default=DEFAULT_PERFORMANCE_MINUTES)

    venue_name: Mapped[str | None] = mapped_column(String(200))
    venue_address: Mapped[str | None] = mapped_column(String(300))
    pay_cents: Mapped[int | None]

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    slots: Mapped[list["GigSlot"]] = relationship(
        back_populates="gig",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="GigSlot.id",
    )
    contacts: Mapped[list["GigContact"]] = relationship(
        back_populates="gig",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="GigContact.id",
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

    @property
    def end_at(self) -> datetime | None:
        if self.first_set_at is None:
            return None
        return self.first_set_at + timedelta(minutes=self.performance_minutes)

    def slot_for(self, member_id: int) -> "GigSlot | None":
        return next((slot for slot in self.slots if slot.member_id == member_id), None)


class GigSlot(Base):
    """One role the gig needs, and who has been asked to fill it."""

    __tablename__ = "gig_slots"
    __table_args__ = (
        UniqueConstraint("gig_id", "role"),
        UniqueConstraint("gig_id", "member_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    gig_id: Mapped[int] = mapped_column(ForeignKey("gigs.id", ondelete="CASCADE"))
    role: Mapped[Role] = mapped_column(str_enum(Role, "slot_role"))
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id"))
    status: Mapped[SlotStatus] = mapped_column(
        str_enum(SlotStatus, "slot_status"), default=SlotStatus.OPEN
    )
    # What the band leader decided this member is paid for the gig.
    pay_cents: Mapped[int | None]
    responded_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    gig: Mapped[Gig] = relationship(back_populates="slots")
    member: Mapped["Member | None"] = relationship(lazy="joined")


class GigContact(Base):
    __tablename__ = "gig_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    gig_id: Mapped[int] = mapped_column(ForeignKey("gigs.id", ondelete="CASCADE"))
    label: Mapped[ContactLabel] = mapped_column(
        str_enum(ContactLabel, "contact_label"), default=ContactLabel.VENUE
    )
    name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(254))
    notes: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    gig: Mapped[Gig] = relationship(back_populates="contacts")

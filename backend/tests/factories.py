"""Builders for test data. Each one commits, so the API under test can see the rows."""

from datetime import UTC, datetime
from itertools import count
from typing import Any

from sqlalchemy.orm import Session

from app.models.availability import BusyTime
from app.models.enums import ContactLabel, GigStatus, InvitationStatus, Role, SlotStatus
from app.models.gig import Gig, GigContact, GigSlot
from app.models.member import Member
from app.models.practice import Practice, PracticeInvitation

BLUE_DOOR_FIRST_SET = datetime(2026, 10, 19, 0, 0, tzinfo=UTC)

_ids = count(1)


def complete_gig_fields() -> dict[str, Any]:
    """Every gig field booking needs (contacts and lineup are added separately)."""
    return {
        "first_set_at": BLUE_DOOR_FIRST_SET,
        "venue_name": "The Blue Door",
        "venue_address": "123 Main St",
        "pay_cents": 40_000,
    }


def headers_for(member: Member) -> dict[str, str]:
    return {"X-Acting-Member-Id": str(member.id)}


class Factory:
    def __init__(self, session: Session) -> None:
        self.session = session

    def member(
        self,
        *,
        name: str | None = None,
        role: Role | None = Role.BASS,
        leader: bool = False,
        phone: str | None = None,
    ) -> Member:
        n = next(_ids)
        member = Member(
            name=name or f"Member {n}",
            email=f"member{n}@example.com",
            phone=phone,
            primary_role=role,
            is_manager=False,
            is_band_leader=leader,
        )
        self.session.add(member)
        self.session.commit()
        return member

    def leader(self, *, name: str = "Sam Rivera") -> Member:
        return self.member(name=name, role=Role.RHYTHM_GUITAR_VOCALS, leader=True)

    def manager(self, *, name: str = "Jordan Avery") -> Member:
        n = next(_ids)
        manager = Member(name=name, email=f"manager{n}@example.com", is_manager=True)
        self.session.add(manager)
        self.session.commit()
        return manager

    def gig(self, *, status: GigStatus = GigStatus.POTENTIAL, **fields: Any) -> Gig:
        gig = Gig(status=status, **fields)
        self.session.add(gig)
        self.session.commit()
        return gig

    def slot(
        self,
        gig: Gig,
        role: Role,
        member: Member | None = None,
        status: SlotStatus | None = None,
        pay_cents: int | None = None,
    ) -> GigSlot:
        if status is None:
            status = SlotStatus.OPEN if member is None else SlotStatus.INVITED
        slot = GigSlot(gig=gig, role=role, member=member, status=status, pay_cents=pay_cents)
        self.session.add(slot)
        self.session.commit()
        return slot

    def contact(self, gig: Gig, **fields: Any) -> GigContact:
        fields.setdefault("label", ContactLabel.VENUE)
        contact = GigContact(gig=gig, **fields)
        self.session.add(contact)
        self.session.commit()
        return contact

    def bookable_gig(
        self,
        *,
        status: GigStatus = GigStatus.POTENTIAL,
        leader: Member | None = None,
        **fields: Any,
    ) -> Gig:
        """A gig with everything booking needs: details, a contact, and the leader accepted."""
        gig = self.gig(status=status, **{**complete_gig_fields(), **fields})
        self.contact(gig, name="Pat Lee", phone="555-0142")
        self.slot(
            gig,
            Role.RHYTHM_GUITAR_VOCALS,
            leader or self.leader(),
            SlotStatus.ACCEPTED,
            pay_cents=20_000,
        )
        self.session.refresh(gig)
        return gig

    def busy_time(self, member: Member, starts_at: datetime, ends_at: datetime) -> BusyTime:
        busy_time = BusyTime(member_id=member.id, starts_at=starts_at, ends_at=ends_at)
        self.session.add(busy_time)
        self.session.commit()
        return busy_time

    def practice(
        self,
        starts_at: datetime,
        invitees: list[Member],
        *,
        scheduled_by: Member | None = None,
        status: InvitationStatus = InvitationStatus.INVITED,
        **fields: Any,
    ) -> Practice:
        practice = Practice(
            starts_at=starts_at,
            scheduled_by_id=(scheduled_by or self.manager()).id,
            invitations=[PracticeInvitation(member_id=m.id, status=status) for m in invitees],
            **fields,
        )
        self.session.add(practice)
        self.session.commit()
        return practice

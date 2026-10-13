"""Builders for test data. Each one commits, so the API under test can see the rows."""

from datetime import UTC, datetime
from itertools import count
from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import GigStatus, GigType, Role
from app.models.gig import Gig, GigAssignment
from app.models.member import Member

BLUE_DOOR_FIRST_SET = datetime(2026, 10, 19, 0, 0, tzinfo=UTC)

_ids = count(1)


def complete_gig_fields() -> dict[str, Any]:
    """Every field a gig needs before it can be booked."""
    return {
        "first_set_at": BLUE_DOOR_FIRST_SET,
        "venue_name": "The Blue Door",
        "venue_address": "123 Main St",
        "gig_type": GigType.DUO,
        "pay_cents": 40_000,
        "venue_contact_name": "Pat Lee",
        "venue_contact_phone": "555-0142",
    }


def headers_for(member: Member) -> dict[str, str]:
    return {"X-Acting-Member-Id": str(member.id)}


class Factory:
    def __init__(self, session: Session) -> None:
        self.session = session

    def member(self, *, name: str | None = None, role: Role | None = Role.BASS) -> Member:
        n = next(_ids)
        member = Member(
            name=name or f"Member {n}",
            email=f"member{n}@example.com",
            primary_role=role,
            is_manager=False,
        )
        self.session.add(member)
        self.session.commit()
        return member

    def manager(self, *, name: str = "Jordan Avery") -> Member:
        n = next(_ids)
        manager = Member(name=name, email=f"manager{n}@example.com", is_manager=True)
        self.session.add(manager)
        self.session.commit()
        return manager

    def gig(self, *, status: GigStatus = GigStatus.POTENTIAL, **fields: Any) -> Gig:
        fields.setdefault("load_in_offset_minutes", 120)
        fields.setdefault("soundcheck_offset_minutes", 60)
        gig = Gig(status=status, **fields)
        self.session.add(gig)
        self.session.commit()
        return gig

    def complete_gig(self, *, status: GigStatus = GigStatus.POTENTIAL, **fields: Any) -> Gig:
        return self.gig(status=status, **{**complete_gig_fields(), **fields})

    def assign(self, gig: Gig, member: Member, slot: Role) -> GigAssignment:
        assignment = GigAssignment(gig_id=gig.id, member_id=member.id, slot=slot)
        self.session.add(assignment)
        self.session.commit()
        self.session.refresh(gig)
        return assignment

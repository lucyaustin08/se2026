from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import GigStatus, SlotStatus
from app.models.gig import Gig, GigContact, GigSlot
from app.schemas.gigs import GigSort

_ORDER_BY: dict[GigSort, tuple[ColumnElement[Any], ...]] = {
    GigSort.FIRST_SET_AT: (Gig.first_set_at.asc().nulls_last(),),
    GigSort.FIRST_SET_AT_DESC: (Gig.first_set_at.desc().nulls_last(),),
    GigSort.CREATED_AT: (Gig.created_at.asc(),),
    GigSort.CREATED_AT_DESC: (Gig.created_at.desc(),),
    GigSort.VENUE_NAME: (Gig.venue_name.asc().nulls_last(),),
    GigSort.VENUE_NAME_DESC: (Gig.venue_name.desc().nulls_last(),),
}


@dataclass(frozen=True, slots=True)
class MemberSlotFilter:
    """Keep only gigs where `member_id` holds a slot whose status is in `slot_statuses`.

    Gigs whose own status is in `except_gig_statuses` are kept either way.
    """

    member_id: int
    slot_statuses: frozenset[SlotStatus]
    except_gig_statuses: frozenset[GigStatus] = frozenset()


class GigRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, gig_id: int) -> Gig | None:
        return self._session.get(Gig, gig_id)

    def add(self, gig: Gig) -> None:
        self._session.add(gig)

    def search(
        self,
        *,
        q: str | None,
        statuses: Collection[GigStatus] | None,
        has_date: bool | None,
        member_slot: MemberSlotFilter | None,
        sort: GigSort,
        page: int,
        page_size: int,
    ) -> tuple[list[Gig], int]:
        """Return one page of gigs matching every given filter, plus the total match count."""
        stmt = select(Gig)
        if statuses is not None:
            stmt = stmt.where(Gig.status.in_(list(statuses)))
        if has_date is True:
            stmt = stmt.where(Gig.first_set_at.is_not(None))
        elif has_date is False:
            stmt = stmt.where(Gig.first_set_at.is_(None))
        if member_slot is not None:
            holds_slot = Gig.slots.any(
                and_(
                    GigSlot.member_id == member_slot.member_id,
                    GigSlot.status.in_(list(member_slot.slot_statuses)),
                )
            )
            if member_slot.except_gig_statuses:
                stmt = stmt.where(
                    or_(Gig.status.in_(list(member_slot.except_gig_statuses)), holds_slot)
                )
            else:
                stmt = stmt.where(holds_slot)
        if q:
            stmt = stmt.where(
                or_(
                    Gig.venue_name.icontains(q, autoescape=True),
                    Gig.venue_address.icontains(q, autoescape=True),
                    Gig.contacts.any(GigContact.name.icontains(q, autoescape=True)),
                )
            )

        total = self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(*_ORDER_BY[sort], Gig.id).limit(page_size).offset((page - 1) * page_size)
        )
        return list(self._session.scalars(stmt)), total

    def accepted_by_member(self, member_id: int, *, exclude_gig_id: int) -> list[Gig]:
        """Every other gig (not cancelled) where the member has accepted a slot."""
        stmt = select(Gig).where(
            Gig.id != exclude_gig_id,
            Gig.status != GigStatus.CANCELLED,
            Gig.slots.any(
                and_(GigSlot.member_id == member_id, GigSlot.status == SlotStatus.ACCEPTED)
            ),
        )
        return list(self._session.scalars(stmt))

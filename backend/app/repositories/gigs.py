from collections.abc import Collection

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import GigStatus
from app.models.gig import Gig, GigAssignment
from app.schemas.gigs import GigSort

_ORDER_BY = {
    GigSort.FIRST_SET_AT: (Gig.first_set_at.asc().nulls_last(),),
    GigSort.FIRST_SET_AT_DESC: (Gig.first_set_at.desc().nulls_last(),),
    GigSort.CREATED_AT: (Gig.created_at.asc(),),
    GigSort.CREATED_AT_DESC: (Gig.created_at.desc(),),
    GigSort.VENUE_NAME: (Gig.venue_name.asc().nulls_last(),),
    GigSort.VENUE_NAME_DESC: (Gig.venue_name.desc().nulls_last(),),
}

_SEARCHABLE = (
    Gig.venue_name,
    Gig.venue_address,
    Gig.venue_contact_name,
    Gig.booking_contact_name,
)


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
        assigned_member_id: int | None,
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
        if assigned_member_id is not None:
            stmt = stmt.where(Gig.assignments.any(GigAssignment.member_id == assigned_member_id))
        if q:
            stmt = stmt.where(or_(*(col.icontains(q, autoescape=True) for col in _SEARCHABLE)))

        total = self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(*_ORDER_BY[sort], Gig.id).limit(page_size).offset((page - 1) * page_size)
        )
        return list(self._session.scalars(stmt)), total

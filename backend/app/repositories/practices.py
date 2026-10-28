from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.practice import Practice, PracticeInvitation
from app.schemas.practices import PracticeSort

_ORDER_BY = {
    PracticeSort.STARTS_AT: Practice.starts_at.asc(),
    PracticeSort.STARTS_AT_DESC: Practice.starts_at.desc(),
}


class PracticeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, practice_id: int) -> Practice | None:
        return self._session.get(Practice, practice_id)

    def add(self, practice: Practice) -> Practice:
        self._session.add(practice)
        self._session.flush()
        return practice

    def search(
        self,
        *,
        q: str | None,
        invited_member_id: int | None,
        starts_after: datetime | None,
        starts_before: datetime | None,
        sort: PracticeSort,
        page: int,
        page_size: int,
    ) -> tuple[list[Practice], int]:
        stmt = select(Practice)
        if invited_member_id is not None:
            stmt = stmt.where(
                Practice.invitations.any(PracticeInvitation.member_id == invited_member_id)
            )
        if starts_after is not None:
            stmt = stmt.where(Practice.starts_at >= starts_after)
        if starts_before is not None:
            stmt = stmt.where(Practice.starts_at < starts_before)
        if q:
            stmt = stmt.where(
                or_(
                    Practice.location.icontains(q, autoescape=True),
                    Practice.notes.icontains(q, autoescape=True),
                )
            )

        total = self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(_ORDER_BY[sort], Practice.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return list(self._session.scalars(stmt)), total

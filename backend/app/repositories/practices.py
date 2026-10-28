from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import InvitationStatus
from app.models.practice import Practice, PracticeInvitation
from app.schemas.practices import MAX_PRACTICE_MINUTES, PracticeSort

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

    def overlapping_for_member(
        self, member_id: int, start: datetime, end: datetime
    ) -> list[Practice]:
        """Practices the member is invited to or coming to (not declined) that overlap
        [start, end). Touching ends don't count."""
        stmt = select(Practice).where(
            Practice.starts_at < end,
            # No practice is longer than the maximum length, so nothing earlier can overlap.
            Practice.starts_at > start - timedelta(minutes=MAX_PRACTICE_MINUTES),
            Practice.invitations.any(
                (PracticeInvitation.member_id == member_id)
                & (PracticeInvitation.status != InvitationStatus.DECLINED)
            ),
        )
        # The end is computed from the length, so the last check happens here, not in SQL.
        return [p for p in self._session.scalars(stmt) if p.ends_at > start]

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.availability import BusyTime
from app.schemas.availability import BusyTimeSort

_ORDER_BY = {
    BusyTimeSort.STARTS_AT: BusyTime.starts_at.asc(),
    BusyTimeSort.STARTS_AT_DESC: BusyTime.starts_at.desc(),
}


class BusyTimeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, busy_time_id: int) -> BusyTime | None:
        return self._session.get(BusyTime, busy_time_id)

    def add(self, busy_time: BusyTime) -> BusyTime:
        self._session.add(busy_time)
        self._session.flush()
        return busy_time

    def delete(self, busy_time: BusyTime) -> None:
        self._session.delete(busy_time)

    def search(
        self,
        *,
        member_id: int | None,
        ends_after: datetime | None,
        starts_before: datetime | None,
        sort: BusyTimeSort,
        page: int,
        page_size: int,
    ) -> tuple[list[BusyTime], int]:
        stmt = select(BusyTime)
        if member_id is not None:
            stmt = stmt.where(BusyTime.member_id == member_id)
        if ends_after is not None:
            stmt = stmt.where(BusyTime.ends_at > ends_after)
        if starts_before is not None:
            stmt = stmt.where(BusyTime.starts_at < starts_before)

        total = self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(_ORDER_BY[sort], BusyTime.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return list(self._session.scalars(stmt)), total

    def overlapping(self, member_id: int, start: datetime, end: datetime) -> list[BusyTime]:
        """The member's busy times that overlap [start, end). Touching ends don't count."""
        stmt = (
            select(BusyTime)
            .where(
                BusyTime.member_id == member_id,
                BusyTime.starts_at < end,
                BusyTime.ends_at > start,
            )
            .order_by(BusyTime.starts_at)
        )
        return list(self._session.scalars(stmt))

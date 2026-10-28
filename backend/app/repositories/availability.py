from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.availability import BusyTime, RecurringBusyTime
from app.schemas.availability import BusyTimeSort, RecurringBusyTimeSort

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

    def overlapping_any(
        self, start: datetime, end: datetime, *, member_ids: Collection[int] | None
    ) -> list[BusyTime]:
        """Busy times overlapping [start, end) for these members, or everyone's for None."""
        stmt = select(BusyTime).where(BusyTime.starts_at < end, BusyTime.ends_at > start)
        if member_ids is not None:
            stmt = stmt.where(BusyTime.member_id.in_(list(member_ids)))
        return list(self._session.scalars(stmt.order_by(BusyTime.starts_at, BusyTime.id)))

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


@dataclass(frozen=True, slots=True)
class Occurrence:
    """One day's stretch of a weekly busy time, as real moments."""

    rule_id: int
    member_id: int
    starts_at: datetime
    ends_at: datetime


_RECURRING_ORDER_BY = {
    RecurringBusyTimeSort.STARTS_ON: RecurringBusyTime.starts_on.asc(),
    RecurringBusyTimeSort.STARTS_ON_DESC: RecurringBusyTime.starts_on.desc(),
}

# PostgreSQL turns each weekly rule into real moments. For every local date the rule covers
# (starting a day early, in case the day before runs past midnight into the range), it keeps
# the dates whose ISO weekday is in the rule, adds the local clock times to them, and converts
# with AT TIME ZONE using the rule's time zone, which applies daylight saving for that date.
# An end time at or before the start time ends on the next day.
_OCCURRENCES_SQL = text(
    """
    SELECT rule_id, member_id, starts_at, ends_at
    FROM (
        SELECT
            r.id AS rule_id,
            r.member_id,
            (d.day + r.start_time) AT TIME ZONE r.time_zone AS starts_at,
            (
                d.day + r.end_time
                + CASE WHEN r.end_time <= r.start_time THEN interval '1 day' ELSE interval '0' END
            ) AT TIME ZONE r.time_zone AS ends_at
        FROM recurring_busy_times AS r
        CROSS JOIN LATERAL (
            SELECT CAST(g AS date) AS day
            FROM generate_series(
                CAST(GREATEST(
                    r.starts_on,
                    CAST(CAST(:range_start AS timestamptz) AT TIME ZONE r.time_zone AS date) - 1
                ) AS timestamp),
                CAST(LEAST(
                    COALESCE(r.ends_on, CAST('infinity' AS date)),
                    CAST(CAST(:range_end AS timestamptz) AT TIME ZONE r.time_zone AS date)
                ) AS timestamp),
                interval '1 day'
            ) AS g
        ) AS d
        WHERE CAST(EXTRACT(ISODOW FROM d.day) AS integer) = ANY(r.weekdays)
          AND (:every_member OR r.member_id = ANY(:member_ids))
    ) AS occurrence
    WHERE starts_at < CAST(:range_end AS timestamptz)
      AND ends_at > CAST(:range_start AS timestamptz)
    ORDER BY starts_at, rule_id
    """
)


class RecurringBusyTimeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, rule_id: int) -> RecurringBusyTime | None:
        return self._session.get(RecurringBusyTime, rule_id)

    def add(self, rule: RecurringBusyTime) -> RecurringBusyTime:
        self._session.add(rule)
        self._session.flush()
        return rule

    def delete(self, rule: RecurringBusyTime) -> None:
        self._session.delete(rule)

    def search(
        self,
        *,
        member_id: int | None,
        sort: RecurringBusyTimeSort,
        page: int,
        page_size: int,
    ) -> tuple[list[RecurringBusyTime], int]:
        stmt = select(RecurringBusyTime)
        if member_id is not None:
            stmt = stmt.where(RecurringBusyTime.member_id == member_id)
        total = self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(_RECURRING_ORDER_BY[sort], RecurringBusyTime.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return list(self._session.scalars(stmt)), total

    def occurrences(
        self, start: datetime, end: datetime, *, member_ids: Collection[int] | None
    ) -> list[Occurrence]:
        """Every day's stretch of the weekly busy times that overlaps [start, end), earliest
        first. `member_ids=None` means everyone's."""
        if member_ids is not None and not member_ids:
            return []
        rows = self._session.execute(
            _OCCURRENCES_SQL,
            {
                "range_start": start,
                "range_end": end,
                "every_member": member_ids is None,
                # Never used when every_member is true; a real value keeps the type clear.
                "member_ids": list(member_ids) if member_ids is not None else [0],
            },
        )
        return [
            Occurrence(
                rule_id=row.rule_id,
                member_id=row.member_id,
                starts_at=row.starts_at,
                ends_at=row.ends_at,
            )
            for row in rows
        ]

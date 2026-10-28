"""PostgreSQL turns weekly rules into real moments. These tests check the database's own
time zone handling, so they only make sense on PostgreSQL."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.repositories.availability import RecurringBusyTimeRepository
from app.schemas.availability import RecurringBusyTimeSort
from app.schemas.pagination import MAX_PAGE_SIZE
from tests.factories import Factory

WEEKDAYS = [1, 2, 3, 4, 5]


def utc(month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=UTC)


def test_weekdays_8_to_5_keep_their_clock_time_across_daylight_saving(
    db: Session, make: Factory
) -> None:
    riley = make.member()
    # Mon, Oct 26 to Fri, Nov 6, 2026. Daylight saving ends on Sun, Nov 1.
    make.weekly(riley, WEEKDAYS, time(8), time(17), date(2026, 10, 26), date(2026, 11, 6))

    found = RecurringBusyTimeRepository(db).occurrences(
        utc(10, 26, 0), utc(11, 8, 0), member_ids=None
    )

    assert len(found) == 10
    fri = next(o for o in found if o.starts_at.date() == date(2026, 10, 30))
    mon = next(o for o in found if o.starts_at.date() == date(2026, 11, 2))
    # 8:00 AM is 12:00 UTC under daylight time (UTC-4) and 13:00 UTC under standard (UTC-5).
    assert (fri.starts_at, fri.ends_at) == (utc(10, 30, 12), utc(10, 30, 21))
    assert (mon.starts_at, mon.ends_at) == (utc(11, 2, 13), utc(11, 2, 22))


def test_an_end_before_the_start_runs_past_midnight(db: Session, make: Factory) -> None:
    riley = make.member()
    # Saturdays, 10:00 PM to 2:00 AM.
    make.weekly(riley, [6], time(22), time(2), date(2026, 11, 7))

    (found,) = RecurringBusyTimeRepository(db).occurrences(
        utc(11, 7, 12), utc(11, 8, 12), member_ids=None
    )

    # 10:00 PM Sat, Nov 7 to 2:00 AM Sun, Nov 8 Eastern standard time.
    assert (found.starts_at, found.ends_at) == (utc(11, 8, 3), utc(11, 8, 7))


def test_an_overnight_stretch_from_the_day_before_the_range_is_included(
    db: Session, make: Factory
) -> None:
    riley = make.member()
    make.weekly(riley, [6], time(22), time(2), date(2026, 11, 7))

    # The range starts at 1:00 AM Sunday local time, inside Saturday night's busy time.
    found = RecurringBusyTimeRepository(db).occurrences(
        utc(11, 8, 6), utc(11, 8, 20), member_ids=None
    )

    assert [o.starts_at for o in found] == [utc(11, 8, 3)]


def test_the_first_and_last_dates_are_respected(db: Session, make: Factory) -> None:
    riley = make.member()
    # Tuesdays only, Nov 10 to Nov 17 inclusive.
    make.weekly(riley, [2], time(18), time(21), date(2026, 11, 10), date(2026, 11, 17))

    found = RecurringBusyTimeRepository(db).occurrences(
        utc(11, 1, 0), utc(12, 1, 0), member_ids=None
    )

    assert [o.starts_at for o in found] == [utc(11, 10, 23), utc(11, 17, 23)]


def test_without_a_last_date_it_keeps_going(db: Session, make: Factory) -> None:
    riley = make.member()
    make.weekly(riley, [2], time(18), time(21), date(2026, 11, 10))

    found = RecurringBusyTimeRepository(db).occurrences(
        datetime(2027, 3, 1, tzinfo=UTC), datetime(2027, 3, 8, tzinfo=UTC), member_ids=None
    )

    # Tue, Mar 2, 2027, 6:00 PM Eastern standard time.
    assert [o.starts_at for o in found] == [datetime(2027, 3, 2, 23, 0, tzinfo=UTC)]


def test_filters_by_member(db: Session, make: Factory) -> None:
    riley = make.member()
    casey = make.member()
    make.weekly(riley, [2], time(18), time(21), date(2026, 11, 10))
    rule = make.weekly(casey, [2], time(18), time(21), date(2026, 11, 10))
    repo = RecurringBusyTimeRepository(db)

    found = repo.occurrences(utc(11, 9, 0), utc(11, 12, 0), member_ids=[casey.id])

    assert [(o.rule_id, o.member_id) for o in found] == [(rule.id, casey.id)]
    assert repo.occurrences(utc(11, 9, 0), utc(11, 12, 0), member_ids=[]) == []


def test_touching_the_range_doesnt_count(db: Session, make: Factory) -> None:
    riley = make.member()
    make.weekly(riley, [2], time(18), time(21), date(2026, 11, 10))
    repo = RecurringBusyTimeRepository(db)

    # The busy time is 23:00 to 02:00 UTC. A range ending at 23:00 or starting at 02:00 only
    # touches it.
    assert repo.occurrences(utc(11, 10, 12), utc(11, 10, 23), member_ids=None) == []
    assert repo.occurrences(utc(11, 11, 2), utc(11, 11, 12), member_ids=None) == []


def test_search_sorts_and_pages(db: Session, make: Factory) -> None:
    riley = make.member()
    ids = [
        make.weekly(riley, [1], time(9), time(10), date(2026, 11, 1) + timedelta(days=d)).id
        for d in (2, 0, 1)
    ]
    later, first, middle = ids
    repo = RecurringBusyTimeRepository(db)

    def search(**kw: object) -> tuple[list[int], int]:
        params: dict[str, object] = {
            "member_id": None,
            "sort": RecurringBusyTimeSort.STARTS_ON,
            "page": 1,
            "page_size": 25,
        }
        params.update(kw)
        items, total = repo.search(**params)  # type: ignore[arg-type]
        return [r.id for r in items], total

    assert search()[0] == [first, middle, later]
    assert search(sort=RecurringBusyTimeSort.STARTS_ON_DESC)[0] == [later, middle, first]
    assert search(page=1, page_size=1) == ([first], 3)
    assert search(page=4, page_size=1) == ([], 3)
    assert search(page_size=MAX_PAGE_SIZE) == ([first, middle, later], 3)
    assert search(member_id=make.member().id) == ([], 0)

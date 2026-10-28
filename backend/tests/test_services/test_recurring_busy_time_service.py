"""Weekly busy times, tested through the service with a real database."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.availability import RecurringBusyTime
from app.models.member import Member
from app.schemas.availability import (
    BusyPeriodKind,
    BusyPeriodsQuery,
    ConflictKind,
    RecurringBusyTimeIn,
    RecurringBusyTimePage,
    RecurringBusyTimeSort,
)
from app.services.availability import AvailabilityService
from tests.factories import BLUE_DOOR_FIRST_SET, Factory

# The Blue Door gig is on Sun, Oct 18, 2026: soundcheck 7:00 PM, first set 8:00 PM, done at
# 11:00 PM Eastern daylight time (23:00 to 03:00 UTC).
SOUNDCHECK = BLUE_DOOR_FIRST_SET - timedelta(hours=1)
SUNDAY = 7


@pytest.fixture
def service(db: Session) -> AvailabilityService:
    return AvailabilityService(db)


def weekly_in(**fields: object) -> RecurringBusyTimeIn:
    data: dict[str, object] = {
        "weekdays": [2, 4],
        "start_time": "18:00",
        "end_time": "21:00",
        "starts_on": "2026-11-01",
    }
    data.update(fields)
    return RecurringBusyTimeIn.model_validate(data)


def list_for(
    service: AvailabilityService, actor: Member, member_id: int | None = None
) -> RecurringBusyTimePage:
    return service.list_recurring(
        actor, member_id=member_id, sort=RecurringBusyTimeSort.STARTS_ON, page=1, page_size=25
    )


def periods(start: datetime, end: datetime) -> BusyPeriodsQuery:
    return BusyPeriodsQuery(ends_after=start, starts_before=end)


# ---- Adding, changing and deleting -----------------------------------------------------------


def test_a_member_adds_a_weekly_busy_time_in_the_bands_time_zone(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member(name="Riley Chen")

    added = service.add_recurring(riley, weekly_in(weekdays=[4, 2, 4]))

    assert added.member.name == "Riley Chen"
    # Each day once, Monday first.
    assert added.weekdays == [2, 4]
    assert (added.start_time, added.end_time) == (time(18), time(21))
    assert (added.starts_on, added.ends_on) == (date(2026, 11, 1), None)
    assert added.time_zone == "America/New_York"
    assert db.get(RecurringBusyTime, added.id) is not None


def test_a_member_changes_their_own_weekly_busy_time(
    service: AvailabilityService, make: Factory
) -> None:
    riley = make.member()
    rule = make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))

    changed = service.change_recurring(
        riley, rule.id, weekly_in(weekdays=[6, 7], ends_on="2026-12-31")
    )

    assert (changed.weekdays, changed.ends_on) == ([6, 7], date(2026, 12, 31))


def test_a_member_deletes_their_own_weekly_busy_time(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    rule = make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))
    rule_id = rule.id

    service.delete_recurring(riley, rule_id)

    db.expire_all()
    assert db.get(RecurringBusyTime, rule_id) is None


@pytest.mark.parametrize("actor", ["member", "leader", "manager"])
def test_nobody_changes_or_deletes_someone_elses_weekly_busy_time(
    service: AvailabilityService, make: Factory, actor: str
) -> None:
    rule = make.weekly(make.member(), [2], time(18), time(21), date(2026, 11, 1))
    someone: Member = getattr(make, actor)()

    with pytest.raises(PermissionDeniedError) as changing:
        service.change_recurring(someone, rule.id, weekly_in())
    with pytest.raises(PermissionDeniedError) as deleting:
        service.delete_recurring(someone, rule.id)

    assert changing.value.code == deleting.value.code == "not_your_busy_time"


def test_a_missing_weekly_busy_time_is_not_found(
    service: AvailabilityService, make: Factory
) -> None:
    with pytest.raises(NotFoundError) as caught:
        service.delete_recurring(make.member(), 9999)

    assert caught.value.code == "recurring_busy_time_not_found"


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"end_time": "18:00"}, "different from the start time"),
        ({"ends_on": "2026-10-31"}, "can't be before the first date"),
        ({"weekdays": []}, "at least 1 item"),
        ({"weekdays": [0]}, "greater than or equal to 1"),
        ({"weekdays": [8]}, "less than or equal to 7"),
        ({"reason": "work"}, "Extra inputs are not permitted"),
    ],
)
def test_a_weekly_busy_time_has_to_make_sense(fields: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        weekly_in(**fields)


def test_an_end_time_before_the_start_time_is_allowed() -> None:
    # It runs past midnight.
    assert weekly_in(start_time="22:00", end_time="02:00").end_time == time(2)


# ---- Who sees them ---------------------------------------------------------------------------


def test_a_member_lists_only_their_own_weekly_busy_times(
    service: AvailabilityService, make: Factory
) -> None:
    riley, casey = make.member(), make.member()
    mine = make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))
    make.weekly(casey, [3], time(18), time(21), date(2026, 11, 1))

    page = list_for(service, riley)

    assert [item.id for item in page.items] == [mine.id]
    with pytest.raises(PermissionDeniedError) as caught:
        list_for(service, riley, member_id=casey.id)
    assert caught.value.code == "availability_private"


@pytest.mark.parametrize("actor", ["leader", "manager"])
def test_the_manager_and_band_leader_see_everyones_weekly_busy_times(
    service: AvailabilityService, make: Factory, actor: str
) -> None:
    riley, casey = make.member(), make.member()
    make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))
    caseys = make.weekly(casey, [3], time(18), time(21), date(2026, 11, 1))
    someone: Member = getattr(make, actor)()

    assert list_for(service, someone).total == 2
    assert [item.id for item in list_for(service, someone, casey.id).items] == [caseys.id]


# ---- Every busy period in a range, for the calendar -----------------------------------------


def test_busy_periods_combine_one_off_and_weekly_busy_times_in_order(
    service: AvailabilityService, make: Factory
) -> None:
    riley = make.member(name="Riley Chen")
    rule = make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))
    trip = make.busy_time(
        riley,
        datetime(2026, 11, 13, 14, tzinfo=UTC),
        datetime(2026, 11, 15, 23, tzinfo=UTC),
    )

    result = service.busy_periods(
        make.manager(),
        periods(datetime(2026, 11, 8, 5, tzinfo=UTC), datetime(2026, 11, 22, 5, tzinfo=UTC)),
    )

    assert [(p.kind, p.source_id, p.starts_at) for p in result.periods] == [
        # Tue, Nov 10 and Tue, Nov 17 at 6:00 PM Eastern standard time.
        (BusyPeriodKind.WEEKLY, rule.id, datetime(2026, 11, 10, 23, tzinfo=UTC)),
        (BusyPeriodKind.ONE_OFF, trip.id, datetime(2026, 11, 13, 14, tzinfo=UTC)),
        (BusyPeriodKind.WEEKLY, rule.id, datetime(2026, 11, 17, 23, tzinfo=UTC)),
    ]
    assert {p.member.name for p in result.periods} == {"Riley Chen"}


def test_a_member_sees_only_their_own_busy_periods(
    service: AvailabilityService, make: Factory
) -> None:
    riley, casey = make.member(), make.member()
    make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))
    make.weekly(casey, [2], time(18), time(21), date(2026, 11, 1))
    make.busy_time(
        casey, datetime(2026, 11, 12, 14, tzinfo=UTC), datetime(2026, 11, 12, 16, tzinfo=UTC)
    )
    week = periods(datetime(2026, 11, 8, 5, tzinfo=UTC), datetime(2026, 11, 15, 5, tzinfo=UTC))

    assert {p.member.id for p in service.busy_periods(riley, week).periods} == {riley.id}
    assert len(service.busy_periods(make.leader(), week).periods) == 3


def test_the_calendar_asks_for_at_most_62_days() -> None:
    start = datetime(2026, 11, 1, tzinfo=UTC)

    with pytest.raises(ValidationError, match="at most 62 days"):
        periods(start, start + timedelta(days=63))
    with pytest.raises(ValidationError, match="has to be after"):
        periods(start, start)


# ---- Who can play a gig ---------------------------------------------------------------------


def test_a_weekly_busy_time_during_the_gig_marks_the_player_busy(
    service: AvailabilityService, make: Factory
) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    riley = make.member()
    # Sundays 6:00 to 7:30 PM overlaps the first half hour from soundcheck.
    make.weekly(riley, [SUNDAY], time(18), time(19, 30), date(2026, 10, 1))

    availability = service.gig_availability(make.manager(), gig.id)

    (player,) = [p for p in availability.players if p.member.id == riley.id]
    assert player.busy is True
    (conflict,) = player.conflicts
    assert conflict.kind == ConflictKind.WEEKLY_BUSY_TIME
    assert (conflict.starts_at, conflict.ends_at) == (
        SOUNDCHECK - timedelta(hours=1),
        SOUNDCHECK + timedelta(minutes=30),
    )


def test_a_weekly_busy_time_that_ends_at_soundcheck_doesnt_count(
    service: AvailabilityService, make: Factory
) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    riley = make.member()
    make.weekly(riley, [SUNDAY], time(17), time(19), date(2026, 10, 1))

    availability = service.gig_availability(make.manager(), gig.id)

    (player,) = [p for p in availability.players if p.member.id == riley.id]
    assert player.busy is False


def test_a_weekly_busy_time_that_starts_after_the_gig_date_doesnt_count(
    service: AvailabilityService, make: Factory
) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    riley = make.member()
    make.weekly(riley, [SUNDAY], time(18), time(23), date(2026, 10, 19))

    availability = service.gig_availability(make.manager(), gig.id)

    (player,) = [p for p in availability.players if p.member.id == riley.id]
    assert player.busy is False

"""Finding a practice time, tested through the service with a real database."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.errors import PermissionDeniedError
from app.models.enums import InvitationStatus
from app.models.member import Member
from app.schemas.practices import PracticeSuggestionQuery, PracticeSuggestions
from app.services.practices import PracticeService
from tests.factories import Factory

# Searching from Sun, Nov 1, 2026 covers Sun, Nov 8 to Sun, Nov 22. Standard time (UTC-5)
# applies to all of them, so 5:00 PM Eastern is 22:00 UTC.
TODAY = date(2026, 11, 1)


def local(day: int, hour: int, minute: int = 0) -> datetime:
    """A November 2026 wall-clock time in Eastern standard time, as UTC."""
    return datetime(2026, 11, day, tzinfo=UTC) + timedelta(hours=hour + 5, minutes=minute)


@pytest.fixture
def service(db: Session) -> PracticeService:
    return PracticeService(db)


def suggest(
    service: PracticeService,
    actor: Member,
    invitees: list[Member],
    *,
    today: date = TODAY,
    **query: object,
) -> PracticeSuggestions:
    return service.suggest_times(
        actor,
        PracticeSuggestionQuery.model_validate({"member_ids": [m.id for m in invitees], **query}),
        today=today,
    )


def starts(result: PracticeSuggestions) -> list[datetime]:
    return [s.starts_at for s in result.suggestions]


def test_when_everyone_is_free_each_day_offers_its_earliest_time(
    service: PracticeService, make: Factory
) -> None:
    riley, casey = make.member(), make.member()

    result = suggest(service, make.manager(), [riley, casey])

    assert (result.searched_from, result.searched_to) == (date(2026, 11, 8), date(2026, 11, 22))
    assert starts(result) == [local(day, 17) for day in range(8, 23)]
    assert all(len(s.available) == 2 and s.unavailable == [] for s in result.suggestions)
    assert result.suggestions[0].ends_at == local(8, 20)


def test_a_busy_time_moves_that_day_to_when_everyone_is_free(
    service: PracticeService, make: Factory
) -> None:
    riley = make.member()
    make.busy_time(riley, local(10, 17), local(10, 19))

    result = suggest(service, make.manager(), [riley])

    assert local(10, 19) in starts(result)
    assert local(10, 17) not in starts(result)


def test_a_day_nobody_can_fully_make_ranks_last_and_names_who_cant_come(
    service: PracticeService, make: Factory
) -> None:
    riley = make.member(name="Riley Chen")
    casey = make.member(name="Casey Morgan")
    make.busy_time(riley, local(12, 12), local(12, 23, 30))

    result = suggest(service, make.leader(), [riley, casey])

    last = result.suggestions[-1]
    assert last.starts_at == local(12, 17)
    assert [m.name for m in last.available] == ["Casey Morgan"]
    assert [m.name for m in last.unavailable] == ["Riley Chen"]


def test_times_overlapping_a_gig_are_never_suggested(
    service: PracticeService, make: Factory
) -> None:
    # 8:00 PM on Sat, Nov 14: soundcheck at 7:00 PM, so every 3-hour slot from 5 to 11 clashes.
    make.gig(first_set_at=local(14, 20))

    result = suggest(service, make.manager(), [make.member()])

    assert local(14, 17) not in starts(result)
    assert len(result.suggestions) == 14


def test_a_gig_the_same_day_is_flagged(service: PracticeService, make: Factory) -> None:
    # 11:30 PM on Sun, Nov 15: soundcheck at 10:30 PM, so 5:00 to 8:00 PM is clear.
    make.gig(venue_name="Hub City Tap", first_set_at=local(15, 23, 30))

    result = suggest(service, make.manager(), [make.member()])

    nov_15 = next(s for s in result.suggestions if s.starts_at == local(15, 17))
    assert nov_15.same_day_gig == "Hub City Tap on Sun, Nov 15 at 11:30 PM"
    assert result.suggestions[0].same_day_gig is None


def test_another_practice_counts_unless_declined(service: PracticeService, make: Factory) -> None:
    riley = make.member(name="Riley Chen")
    casey = make.member(name="Casey Morgan")
    make.practice(local(9, 16), [riley])
    make.practice(local(9, 16), [casey], status=InvitationStatus.DECLINED)

    result = suggest(service, make.manager(), [riley, casey])

    # Riley's practice runs 4:00 to 7:00 PM, so the best time that day is 7:00 PM.
    nov_9 = next(s for s in result.suggestions if s.starts_at == local(9, 19))
    assert len(nov_9.available) == 2


def test_the_hours_and_length_choose_the_slots(service: PracticeService, make: Factory) -> None:
    result = suggest(
        service,
        make.manager(),
        [make.member()],
        earliest="10:00",
        latest="12:00",
        length_minutes=120,
    )

    assert starts(result)[0] == local(8, 10)
    assert result.suggestions[0].ends_at == local(8, 12)


def test_wall_clock_times_hold_across_the_end_of_daylight_saving(
    service: PracticeService, make: Factory
) -> None:
    # Searching from Sat, Oct 24 covers Sat, Oct 31 (daylight time) and Sun, Nov 1 (standard).
    result = suggest(service, make.manager(), [make.member()], today=date(2026, 10, 24))

    assert starts(result)[:2] == [
        datetime(2026, 10, 31, 21, 0, tzinfo=UTC),  # 5:00 PM EDT
        datetime(2026, 11, 1, 22, 0, tzinfo=UTC),  # 5:00 PM EST
    ]


def test_only_the_manager_and_band_leader_can_search(
    service: PracticeService, make: Factory
) -> None:
    riley = make.member()

    with pytest.raises(PermissionDeniedError) as error:
        suggest(service, riley, [riley])

    assert error.value.code == "manager_or_band_leader_only"


def test_the_hours_must_fit_the_practice() -> None:
    with pytest.raises(ValueError, match="shorter than the practice"):
        PracticeSuggestionQuery(
            member_ids=[1], earliest=time(18, 0), latest=time(20, 0), length_minutes=180
        )


def test_someone_must_be_invited() -> None:
    with pytest.raises(ValueError):
        PracticeSuggestionQuery(member_ids=[])


def test_default_search_is_5_to_11_pm_for_3_hours() -> None:
    query = PracticeSuggestionQuery(member_ids=[1])

    assert (query.earliest, query.latest, query.length_minutes) == (time(17), time(23), 180)
    assert timedelta(minutes=query.length_minutes) == timedelta(hours=3)

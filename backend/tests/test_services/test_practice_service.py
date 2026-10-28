"""Practice rules, tested through the service with a real (in-memory) database."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleViolation, NotFoundError, PermissionDeniedError
from app.models.enums import GigStatus, InvitationStatus
from app.models.member import Member
from app.models.practice import Practice
from app.schemas.practices import PracticeCreate, PracticePage, PracticeSort
from app.services.practices import PracticeService
from tests.factories import Factory

# A gig at 8:00 PM Eastern on Mon, Oct 19, 2026: soundcheck 7:00 PM, ends 11:00 PM.
GIG_FIRST_SET = datetime(2026, 10, 20, 0, 0, tzinfo=UTC)
GIG_SOUNDCHECK = GIG_FIRST_SET - timedelta(hours=1)
GIG_END = GIG_FIRST_SET + timedelta(hours=3)


@pytest.fixture
def service(db: Session) -> PracticeService:
    return PracticeService(db)


def practice_at(
    starts_at: datetime, invitees: list[Member], minutes: int = 180, **extra: Any
) -> PracticeCreate:
    return PracticeCreate(
        starts_at=starts_at,
        length_minutes=minutes,
        member_ids=[m.id for m in invitees],
        **extra,
    )


def practice_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Practice)) or 0


def list_for(service: PracticeService, actor: Member, **filters: Any) -> PracticePage:
    params: dict[str, Any] = {"q": None, "starts_after": None, "starts_before": None}
    params.update(filters)
    return service.list_practices(
        actor, sort=PracticeSort.STARTS_AT, page=1, page_size=25, **params
    )


# ---- Who can schedule, and who's invited ---------------------------------------------------


def test_the_manager_schedules_a_practice_and_invites_a_group(
    service: PracticeService, make: Factory
) -> None:
    riley = make.member(name="Riley Chen")
    casey = make.member(name="Casey Morgan")

    practice = service.schedule(
        make.manager(),
        practice_at(GIG_FIRST_SET + timedelta(days=3), [riley, casey], location="Sam's garage"),
    )

    assert [(i.member.name, i.status) for i in practice.invitations] == [
        ("Riley Chen", InvitationStatus.INVITED),
        ("Casey Morgan", InvitationStatus.INVITED),
    ]
    assert practice.location == "Sam's garage"
    assert practice.my_status is None


def test_a_band_leader_who_invites_themselves_is_already_coming(
    service: PracticeService, make: Factory
) -> None:
    leader = make.leader()
    riley = make.member()

    practice = service.schedule(
        leader, practice_at(GIG_FIRST_SET + timedelta(days=3), [leader, riley])
    )

    assert practice.my_status is InvitationStatus.ACCEPTED
    assert {i.member.id: i.status for i in practice.invitations}[riley.id] is (
        InvitationStatus.INVITED
    )


def test_ordinary_members_cant_schedule_practices(
    service: PracticeService, make: Factory, db: Session
) -> None:
    riley = make.member()

    with pytest.raises(PermissionDeniedError) as error:
        service.schedule(riley, practice_at(GIG_FIRST_SET + timedelta(days=3), [riley]))

    assert error.value.code == "manager_or_band_leader_only"
    assert practice_count(db) == 0


def test_the_manager_cant_be_invited(service: PracticeService, make: Factory) -> None:
    manager = make.manager()

    with pytest.raises(BusinessRuleViolation) as error:
        service.schedule(manager, practice_at(GIG_FIRST_SET + timedelta(days=3), [manager]))

    assert error.value.code == "manager_cannot_play"


def test_an_unknown_member_cant_be_invited(service: PracticeService, make: Factory) -> None:
    data = PracticeCreate(starts_at=GIG_FIRST_SET + timedelta(days=3), member_ids=[9999])

    with pytest.raises(BusinessRuleViolation) as error:
        service.schedule(make.manager(), data)

    assert error.value.code == "unknown_member"


def test_inviting_someone_twice_invites_them_once(service: PracticeService, make: Factory) -> None:
    riley = make.member()

    practice = service.schedule(
        make.manager(), practice_at(GIG_FIRST_SET + timedelta(days=3), [riley, riley])
    )

    assert len(practice.invitations) == 1


def test_the_end_is_computed_from_the_length(service: PracticeService, make: Factory) -> None:
    start = GIG_FIRST_SET + timedelta(days=3)

    practice = service.schedule(make.manager(), practice_at(start, [make.member()], minutes=150))

    assert practice.ends_at == start + timedelta(minutes=150)


# ---- Conflicts with gigs -------------------------------------------------------------------


@pytest.mark.parametrize("status", [GigStatus.BOOKED, GigStatus.POTENTIAL])
def test_a_practice_overlapping_a_booked_or_pending_gig_is_refused(
    service: PracticeService, make: Factory, db: Session, status: GigStatus
) -> None:
    make.gig(status=status, venue_name="Hub City Tap", first_set_at=GIG_FIRST_SET)

    with pytest.raises(BusinessRuleViolation) as error:
        # 5:00 to 8:00 PM runs into the 7:00 PM soundcheck.
        service.schedule(
            make.manager(), practice_at(GIG_SOUNDCHECK - timedelta(hours=2), [make.member()])
        )

    assert error.value.code == "practice_overlaps_gig"
    assert "Hub City Tap on Mon, Oct 19 at 8:00 PM" in error.value.detail
    assert practice_count(db) == 0


def test_a_cancelled_gig_doesnt_block_a_practice(service: PracticeService, make: Factory) -> None:
    make.gig(status=GigStatus.CANCELLED, first_set_at=GIG_FIRST_SET)

    practice = service.schedule(make.manager(), practice_at(GIG_SOUNDCHECK, [make.member()]))

    assert practice.starts_at == GIG_SOUNDCHECK


def test_a_practice_on_the_same_day_as_a_gig_needs_confirming(
    service: PracticeService, make: Factory, db: Session
) -> None:
    make.gig(venue_name="Hub City Tap", first_set_at=GIG_FIRST_SET)
    # 10:00 AM to 1:00 PM the same day: clear of the gig, but the same day.
    morning = GIG_FIRST_SET - timedelta(hours=10)

    with pytest.raises(BusinessRuleViolation) as error:
        service.schedule(make.manager(), practice_at(morning, [make.member()]))

    assert error.value.code == "practice_same_day_as_gig"
    assert "Hub City Tap" in error.value.detail
    assert practice_count(db) == 0


def test_a_confirmed_same_day_practice_is_scheduled(
    service: PracticeService, make: Factory
) -> None:
    make.gig(first_set_at=GIG_FIRST_SET)
    morning = GIG_FIRST_SET - timedelta(hours=10)

    practice = service.schedule(
        make.manager(), practice_at(morning, [make.member()], confirm_same_day=True)
    )

    assert practice.starts_at == morning


def test_ending_exactly_at_soundcheck_is_not_an_overlap(
    service: PracticeService, make: Factory
) -> None:
    make.gig(first_set_at=GIG_FIRST_SET)

    practice = service.schedule(
        make.manager(),
        practice_at(GIG_SOUNDCHECK - timedelta(hours=3), [make.member()], confirm_same_day=True),
    )

    assert practice.ends_at == GIG_SOUNDCHECK


def test_same_day_means_the_bands_local_day_not_utc(
    service: PracticeService, make: Factory
) -> None:
    make.gig(first_set_at=GIG_FIRST_SET)  # 8:00 PM Mon, Oct 19 locally; Oct 20 in UTC
    # 9:00 AM Tue, Oct 20 locally: the same UTC date as the gig, but the next local day.
    next_morning = datetime(2026, 10, 20, 13, 0, tzinfo=UTC)

    practice = service.schedule(make.manager(), practice_at(next_morning, [make.member()]))

    assert practice.starts_at == next_morning


# ---- Seeing practices ----------------------------------------------------------------------


@pytest.mark.parametrize("who", ["manager", "band leader"])
def test_the_manager_and_band_leader_see_every_practice(
    service: PracticeService, make: Factory, who: str
) -> None:
    make.practice(GIG_FIRST_SET + timedelta(days=1), [make.member()])
    make.practice(GIG_FIRST_SET + timedelta(days=2), [make.member()])
    reader = make.manager() if who == "manager" else make.leader()

    assert list_for(service, reader).total == 2


def test_members_see_only_practices_theyre_invited_to(
    service: PracticeService, make: Factory
) -> None:
    riley = make.member()
    mine = make.practice(GIG_FIRST_SET + timedelta(days=1), [riley])
    declined = make.practice(
        GIG_FIRST_SET + timedelta(days=2), [riley], status=InvitationStatus.DECLINED
    )
    make.practice(GIG_FIRST_SET + timedelta(days=3), [make.member()])

    page = list_for(service, riley)

    assert [p.id for p in page.items] == [mine.id, declined.id]
    assert [p.my_status for p in page.items] == [
        InvitationStatus.INVITED,
        InvitationStatus.DECLINED,
    ]


def test_a_member_not_invited_gets_not_found(service: PracticeService, make: Factory) -> None:
    practice = make.practice(GIG_FIRST_SET + timedelta(days=1), [make.member()])

    with pytest.raises(NotFoundError) as error:
        service.get_practice(make.member(), practice.id)

    assert error.value.code == "practice_not_found"


# ---- Answering -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("accept", "expected"),
    [(True, InvitationStatus.ACCEPTED), (False, InvitationStatus.DECLINED)],
)
def test_an_invited_member_answers(
    service: PracticeService, make: Factory, accept: bool, expected: InvitationStatus
) -> None:
    riley = make.member()
    practice = make.practice(GIG_FIRST_SET + timedelta(days=1), [riley])

    answered = service.answer(riley, practice.id, accept=accept)

    assert answered.my_status is expected
    assert answered.invitations[0].responded_at is not None


def test_answering_twice_is_refused(service: PracticeService, make: Factory) -> None:
    riley = make.member()
    practice = make.practice(
        GIG_FIRST_SET + timedelta(days=1), [riley], status=InvitationStatus.ACCEPTED
    )

    with pytest.raises(BusinessRuleViolation) as error:
        service.answer(riley, practice.id, accept=False)

    assert error.value.code == "invitation_not_pending"


def test_the_manager_cant_answer_a_practice_they_arent_invited_to(
    service: PracticeService, make: Factory
) -> None:
    practice = make.practice(GIG_FIRST_SET + timedelta(days=1), [make.member()])

    with pytest.raises(NotFoundError) as error:
        service.answer(make.manager(), practice.id, accept=True)

    assert error.value.code == "practice_invitation_not_found"


def test_practice_lengths_are_limited() -> None:
    for minutes in (29, 721):
        with pytest.raises(ValueError):
            PracticeCreate(starts_at=GIG_FIRST_SET, length_minutes=minutes, member_ids=[1])


def test_a_practice_needs_someone_invited() -> None:
    with pytest.raises(ValueError):
        PracticeCreate(starts_at=GIG_FIRST_SET, member_ids=[])

"""A busy time over a practice or gig the member is invited to or has accepted."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleViolation
from app.models.availability import BusyTime, RecurringBusyTime
from app.models.enums import GigStatus, InvitationStatus, Role, SlotStatus
from app.models.gig import GigSlot
from app.models.member import Member
from app.models.practice import Practice
from app.schemas.availability import BusyTimeIn, RecurringBusyTimeIn
from app.services.availability import AvailabilityService
from tests.factories import Factory

# Everything here is in March 2027, well after today, in Eastern standard time (UTC-5).
TUESDAY = 2


def local(day: int, hour: int, minute: int = 0) -> datetime:
    """A March 2027 wall-clock time in Eastern standard time, as UTC."""
    return datetime(2027, 3, day, tzinfo=UTC) + timedelta(hours=hour + 5, minutes=minute)


@pytest.fixture
def service(db: Session) -> AvailabilityService:
    return AvailabilityService(db)


def busy(start: datetime, end: datetime, *, decline: bool = False) -> BusyTimeIn:
    return BusyTimeIn(starts_at=start, ends_at=end, decline_invitations=decline)


def tuesday_evenings(*, decline: bool = False, **fields: object) -> RecurringBusyTimeIn:
    data: dict[str, object] = {
        "weekdays": [TUESDAY],
        "start_time": "17:00",
        "end_time": "20:00",
        "starts_on": "2027-03-01",
        "decline_invitations": decline,
    }
    data.update(fields)
    return RecurringBusyTimeIn.model_validate(data)


def practice_tue_6pm(make: Factory, member: Member, status: InvitationStatus) -> Practice:
    """A practice on Tue, Mar 2, 2027, 6:00 to 9:00 PM, at Sam's garage."""
    return make.practice(local(2, 18), [member], status=status, location="Sam's garage")


def count(db: Session, model: type[BusyTime] | type[RecurringBusyTime]) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def invitation_status(db: Session, practice: Practice) -> InvitationStatus:
    db.expire_all()
    return practice.invitations[0].status


# ---- Practices -------------------------------------------------------------------------------


def test_a_busy_time_over_an_accepted_practice_is_refused(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    practice_tue_6pm(make, riley, InvitationStatus.ACCEPTED)

    with pytest.raises(BusinessRuleViolation) as refused:
        service.add_busy_time(riley, busy(local(2, 20), local(2, 22)))

    assert refused.value.code == "busy_time_overlaps_accepted"
    assert refused.value.detail.startswith(
        "You're attending the practice at Sam's garage on Tue, Mar 2 at 6:00 PM then"
    )
    assert count(db, BusyTime) == 0


def test_a_busy_time_over_an_invitation_asks_first(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    practice = practice_tue_6pm(make, riley, InvitationStatus.INVITED)

    with pytest.raises(BusinessRuleViolation) as warned:
        service.add_busy_time(riley, busy(local(2, 17), local(2, 19)))

    assert warned.value.code == "busy_time_overlaps_invitation"
    assert warned.value.detail == (
        "You're invited to the practice at Sam's garage on Tue, Mar 2 at 6:00 PM then. "
        "Add the busy time anyway and decline it?"
    )
    assert count(db, BusyTime) == 0
    assert invitation_status(db, practice) == InvitationStatus.INVITED


def test_confirming_adds_the_busy_time_and_declines_the_invitation(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    practice = practice_tue_6pm(make, riley, InvitationStatus.INVITED)

    service.add_busy_time(riley, busy(local(2, 17), local(2, 19), decline=True))

    assert count(db, BusyTime) == 1
    assert invitation_status(db, practice) == InvitationStatus.DECLINED
    assert practice.invitations[0].responded_at is not None


@pytest.mark.parametrize(
    ("start", "end"),
    [(local(2, 15), local(2, 18)), (local(2, 21), local(2, 23))],
    ids=["ends as it starts", "starts as it ends"],
)
def test_touching_a_practice_isnt_overlapping(
    service: AvailabilityService, make: Factory, start: datetime, end: datetime
) -> None:
    riley = make.member()
    practice_tue_6pm(make, riley, InvitationStatus.ACCEPTED)

    assert service.add_busy_time(riley, busy(start, end)).starts_at == start


def test_declined_practices_and_other_members_practices_dont_count(
    service: AvailabilityService, make: Factory
) -> None:
    riley, casey = make.member(), make.member()
    practice_tue_6pm(make, riley, InvitationStatus.DECLINED)
    make.practice(local(2, 18), [casey], status=InvitationStatus.ACCEPTED)

    added = service.add_busy_time(riley, busy(local(2, 17), local(2, 22)))

    assert added.starts_at == local(2, 17)


def test_practices_that_are_over_dont_count(service: AvailabilityService, make: Factory) -> None:
    riley = make.member()
    yesterday = datetime.now(UTC) - timedelta(days=1)
    make.practice(yesterday, [riley], status=InvitationStatus.ACCEPTED)

    added = service.add_busy_time(riley, busy(yesterday, yesterday + timedelta(hours=1)))

    assert added.starts_at == yesterday


def test_every_overlapping_invitation_is_named_and_declined(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    early = make.practice(local(2, 12), [riley], length_minutes=60)
    late = practice_tue_6pm(make, riley, InvitationStatus.INVITED)

    with pytest.raises(BusinessRuleViolation) as warned:
        service.add_busy_time(riley, busy(local(2, 9), local(2, 23)))
    service.add_busy_time(riley, busy(local(2, 9), local(2, 23), decline=True))

    assert warned.value.detail == (
        "You're invited to the practice on Tue, Mar 2 at 12:00 PM and the practice at Sam's "
        "garage on Tue, Mar 2 at 6:00 PM then. Add the busy time anyway and decline them?"
    )
    assert invitation_status(db, early) == InvitationStatus.DECLINED
    assert invitation_status(db, late) == InvitationStatus.DECLINED


def test_an_accepted_practice_refuses_even_with_confirmation(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    invited = make.practice(local(2, 12), [riley], length_minutes=60)
    practice_tue_6pm(make, riley, InvitationStatus.ACCEPTED)

    with pytest.raises(BusinessRuleViolation) as refused:
        service.add_busy_time(riley, busy(local(2, 9), local(2, 23), decline=True))

    assert refused.value.code == "busy_time_overlaps_accepted"
    # Nothing was declined either.
    assert invitation_status(db, invited) == InvitationStatus.INVITED


def test_changing_a_busy_time_onto_an_accepted_practice_is_refused(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    practice_tue_6pm(make, riley, InvitationStatus.ACCEPTED)
    existing = make.busy_time(riley, local(3, 18), local(3, 21))

    with pytest.raises(BusinessRuleViolation) as refused:
        service.change_busy_time(riley, existing.id, busy(local(2, 18), local(2, 21)))

    assert refused.value.code == "busy_time_overlaps_accepted"
    db.expire_all()
    assert db.get(BusyTime, existing.id).starts_at == local(3, 18)  # type: ignore[union-attr]


# ---- Gigs: soundcheck to the end -----------------------------------------------------------


def gig_tue_8pm(
    make: Factory,
    member: Member,
    status: SlotStatus,
    gig_status: GigStatus = GigStatus.BOOKED,
) -> int:
    """A gig on Tue, Mar 2, 2027: soundcheck 7:00 PM, first set 8:00 PM, done at 11:00 PM."""
    gig = make.gig(status=gig_status, first_set_at=local(2, 20), venue_name="The Blue Door")
    return make.slot(gig, Role.BASS, member, status).id


def test_a_busy_time_over_an_accepted_gig_is_refused(
    service: AvailabilityService, make: Factory
) -> None:
    riley = make.member()
    gig_tue_8pm(make, riley, SlotStatus.ACCEPTED)

    # Overlaps soundcheck only.
    with pytest.raises(BusinessRuleViolation) as refused:
        service.add_busy_time(riley, busy(local(2, 17), local(2, 19, 30)))

    assert refused.value.code == "busy_time_overlaps_accepted"
    assert "The Blue Door on Tue, Mar 2 at 8:00 PM" in refused.value.detail


def test_confirming_over_a_gig_invitation_declines_it(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    slot_id = gig_tue_8pm(make, riley, SlotStatus.INVITED)

    with pytest.raises(BusinessRuleViolation) as warned:
        service.add_busy_time(riley, busy(local(2, 22), local(2, 23)))
    service.add_busy_time(riley, busy(local(2, 22), local(2, 23), decline=True))

    assert warned.value.code == "busy_time_overlaps_invitation"
    db.expire_all()
    slot = db.get(GigSlot, slot_id)
    assert slot is not None and slot.status == SlotStatus.DECLINED
    assert slot.responded_at is not None


def test_a_cancelled_gig_doesnt_count(service: AvailabilityService, make: Factory) -> None:
    riley = make.member()
    gig_tue_8pm(make, riley, SlotStatus.ACCEPTED, gig_status=GigStatus.CANCELLED)

    assert service.add_busy_time(riley, busy(local(2, 19), local(2, 23))).id > 0


# ---- Weekly busy times -----------------------------------------------------------------------


def test_a_weekly_busy_time_over_an_accepted_practice_is_refused(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    practice_tue_6pm(make, riley, InvitationStatus.ACCEPTED)

    with pytest.raises(BusinessRuleViolation) as refused:
        service.add_recurring(riley, tuesday_evenings())

    assert refused.value.code == "busy_time_overlaps_accepted"
    assert count(db, RecurringBusyTime) == 0


def test_a_weekly_busy_time_on_other_days_is_fine(
    service: AvailabilityService, make: Factory
) -> None:
    riley = make.member()
    practice_tue_6pm(make, riley, InvitationStatus.ACCEPTED)

    added = service.add_recurring(riley, tuesday_evenings(weekdays=[1, 3]))

    assert added.weekdays == [1, 3]


def test_a_weekly_busy_time_that_starts_after_the_practice_is_fine(
    service: AvailabilityService, make: Factory
) -> None:
    riley = make.member()
    practice_tue_6pm(make, riley, InvitationStatus.ACCEPTED)

    added = service.add_recurring(riley, tuesday_evenings(starts_on="2027-03-03"))

    assert added.starts_on == date(2027, 3, 3)


def test_confirming_a_weekly_busy_time_declines_the_invitations_it_overlaps(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    this_week = practice_tue_6pm(make, riley, InvitationStatus.INVITED)
    next_week = make.practice(local(9, 18), [riley])
    wednesday = make.practice(local(10, 18), [riley])

    with pytest.raises(BusinessRuleViolation) as warned:
        service.add_recurring(riley, tuesday_evenings())
    service.add_recurring(riley, tuesday_evenings(decline=True))

    assert warned.value.code == "busy_time_overlaps_invitation"
    assert warned.value.detail.endswith("decline them?")
    assert count(db, RecurringBusyTime) == 1
    assert invitation_status(db, this_week) == InvitationStatus.DECLINED
    assert invitation_status(db, next_week) == InvitationStatus.DECLINED
    assert invitation_status(db, wednesday) == InvitationStatus.INVITED


def test_changing_a_weekly_busy_time_onto_an_accepted_practice_keeps_the_old_one(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    practice_tue_6pm(make, riley, InvitationStatus.ACCEPTED)
    rule = make.weekly(riley, [1], time(17), time(20), date(2027, 3, 1))

    with pytest.raises(BusinessRuleViolation):
        service.change_recurring(riley, rule.id, tuesday_evenings())

    db.expire_all()
    kept = db.get(RecurringBusyTime, rule.id)
    assert kept is not None and kept.weekdays == [1]

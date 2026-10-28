"""Busy times and gig availability, tested through the service with a real database."""

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.availability import BusyTime
from app.models.enums import GigStatus, Role, SlotStatus
from app.models.member import Member
from app.schemas.availability import BusyTimeIn, BusyTimePage, BusyTimeSort, ConflictKind
from app.services.availability import AvailabilityService
from tests.factories import BLUE_DOOR_FIRST_SET, Factory

# The Blue Door's first set is BLUE_DOOR_FIRST_SET. With the default offsets, soundcheck is an
# hour before it and the gig ends three hours after it.
SOUNDCHECK = BLUE_DOOR_FIRST_SET - timedelta(hours=1)
END = BLUE_DOOR_FIRST_SET + timedelta(hours=3)


@pytest.fixture
def service(db: Session) -> AvailabilityService:
    return AvailabilityService(db)


def busy_in(minutes_from: int, minutes_to: int) -> BusyTimeIn:
    return BusyTimeIn(
        starts_at=SOUNDCHECK + timedelta(minutes=minutes_from),
        ends_at=SOUNDCHECK + timedelta(minutes=minutes_to),
    )


def list_for(service: AvailabilityService, actor: Member, **filters: Any) -> BusyTimePage:
    params: dict[str, Any] = {"member_id": None, "ends_after": None, "starts_before": None}
    params.update(filters)
    return service.list_busy_times(
        actor, sort=BusyTimeSort.STARTS_AT, page=1, page_size=25, **params
    )


# ---- Adding, changing and deleting your own busy times ---------------------------------------


def test_a_member_adds_a_busy_time_for_themselves(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member(name="Riley Chen")

    added = service.add_busy_time(riley, busy_in(0, 120))

    assert (added.member.name, added.starts_at, added.ends_at) == (
        "Riley Chen",
        SOUNDCHECK,
        SOUNDCHECK + timedelta(hours=2),
    )
    assert db.get(BusyTime, added.id) is not None


def test_a_busy_time_can_run_over_several_days(service: AvailabilityService, make: Factory) -> None:
    riley = make.member()

    added = service.add_busy_time(riley, busy_in(0, 60 * 24 * 5))

    assert added.ends_at - added.starts_at == timedelta(days=5)


def test_the_end_has_to_be_after_the_start() -> None:
    with pytest.raises(ValueError, match="the end has to be after the start"):
        busy_in(60, 60)


def test_a_member_changes_their_own_busy_time(service: AvailabilityService, make: Factory) -> None:
    riley = make.member()
    busy_time = make.busy_time(riley, SOUNDCHECK, END)

    changed = service.change_busy_time(riley, busy_time.id, busy_in(30, 90))

    assert changed.starts_at == SOUNDCHECK + timedelta(minutes=30)


def test_a_member_deletes_their_own_busy_time(
    service: AvailabilityService, make: Factory, db: Session
) -> None:
    riley = make.member()
    busy_time = make.busy_time(riley, SOUNDCHECK, END)

    service.delete_busy_time(riley, busy_time.id)

    db.expire_all()
    assert db.get(BusyTime, busy_time.id) is None


@pytest.mark.parametrize("who", ["member", "manager", "band leader"])
def test_nobody_changes_or_deletes_someone_elses_busy_time(
    service: AvailabilityService, make: Factory, db: Session, who: str
) -> None:
    riley = make.member()
    busy_time = make.busy_time(riley, SOUNDCHECK, END)
    actor = {"member": make.member, "manager": make.manager, "band leader": make.leader}[who]()

    with pytest.raises(PermissionDeniedError) as changing:
        service.change_busy_time(actor, busy_time.id, busy_in(0, 30))
    with pytest.raises(PermissionDeniedError) as deleting:
        service.delete_busy_time(actor, busy_time.id)

    assert changing.value.code == deleting.value.code == "not_your_busy_time"
    db.expire_all()
    assert db.get(BusyTime, busy_time.id) is not None


def test_a_missing_busy_time_is_not_found(service: AvailabilityService, make: Factory) -> None:
    with pytest.raises(NotFoundError) as error:
        service.delete_busy_time(make.member(), 9999)

    assert error.value.code == "busy_time_not_found"


# ---- Who sees busy times --------------------------------------------------------------------


def test_a_member_lists_only_their_own_busy_times(
    service: AvailabilityService, make: Factory
) -> None:
    riley = make.member()
    mine = make.busy_time(riley, SOUNDCHECK, END)
    make.busy_time(make.member(), SOUNDCHECK, END)

    page = list_for(service, riley)

    assert [item.id for item in page.items] == [mine.id]


def test_a_member_cant_list_someone_elses_busy_times(
    service: AvailabilityService, make: Factory
) -> None:
    other = make.member()

    with pytest.raises(PermissionDeniedError) as error:
        list_for(service, make.member(), member_id=other.id)

    assert error.value.code == "availability_private"


@pytest.mark.parametrize("who", ["manager", "band leader"])
def test_the_manager_and_band_leader_see_everyones_busy_times(
    service: AvailabilityService, make: Factory, who: str
) -> None:
    riley = make.member()
    casey = make.member()
    make.busy_time(riley, SOUNDCHECK, END)
    make.busy_time(casey, SOUNDCHECK + timedelta(days=1), END + timedelta(days=1))
    reader = make.manager() if who == "manager" else make.leader()

    everyone = list_for(service, reader)
    only_casey = list_for(service, reader, member_id=casey.id)

    assert {item.member.id for item in everyone.items} == {riley.id, casey.id}
    assert [item.member.id for item in only_casey.items] == [casey.id]


def test_the_list_keeps_busy_times_that_overlap_the_range(
    service: AvailabilityService, make: Factory
) -> None:
    riley = make.member()
    make.busy_time(riley, SOUNDCHECK - timedelta(days=2), SOUNDCHECK - timedelta(days=1))
    during = make.busy_time(riley, SOUNDCHECK - timedelta(hours=1), SOUNDCHECK + timedelta(hours=1))
    make.busy_time(riley, END + timedelta(days=1), END + timedelta(days=2))

    page = list_for(service, riley, ends_after=SOUNDCHECK, starts_before=END)

    assert [item.id for item in page.items] == [during.id]


# ---- Who can play a gig ---------------------------------------------------------------------


def test_a_busy_time_during_the_gig_marks_the_player_busy(
    service: AvailabilityService, make: Factory
) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    riley = make.member(name="Riley Chen")
    make.busy_time(riley, SOUNDCHECK + timedelta(hours=1), SOUNDCHECK + timedelta(hours=2))

    availability = service.gig_availability(make.manager(), gig.id)

    (player,) = [p for p in availability.players if p.member.id == riley.id]
    assert player.busy is True
    assert [c.kind for c in player.conflicts] == [ConflictKind.BUSY_TIME]
    assert (availability.window_starts_at, availability.window_ends_at) == (SOUNDCHECK, END)


def test_a_busy_time_during_load_in_only_doesnt_count(
    service: AvailabilityService, make: Factory
) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    riley = make.member()
    # Busy until exactly soundcheck: they can still get there in time.
    make.busy_time(riley, SOUNDCHECK - timedelta(hours=3), SOUNDCHECK)

    availability = service.gig_availability(make.manager(), gig.id)

    (player,) = [p for p in availability.players if p.member.id == riley.id]
    assert (player.busy, player.conflicts) == (False, [])


def test_another_accepted_gig_marks_the_player_busy(
    service: AvailabilityService, make: Factory
) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    riley = make.member()
    other = make.gig(
        venue_name="Hub City Tap", first_set_at=BLUE_DOOR_FIRST_SET + timedelta(hours=2)
    )
    make.slot(other, Role.BASS, riley, SlotStatus.ACCEPTED)

    availability = service.gig_availability(make.leader(), gig.id)

    (player,) = [p for p in availability.players if p.member.id == riley.id]
    assert [(c.kind, c.venue_name) for c in player.conflicts] == [
        (ConflictKind.GIG, "Hub City Tap")
    ]


def test_cancelled_gigs_and_invitations_dont_count(
    service: AvailabilityService, make: Factory
) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    riley = make.member()
    cancelled = make.gig(status=GigStatus.CANCELLED, first_set_at=BLUE_DOOR_FIRST_SET)
    make.slot(cancelled, Role.BASS, riley, SlotStatus.ACCEPTED)
    invited = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    make.slot(invited, Role.BASS, riley, SlotStatus.INVITED)

    availability = service.gig_availability(make.manager(), gig.id)

    (player,) = [p for p in availability.players if p.member.id == riley.id]
    assert player.busy is False


def test_a_player_with_no_busy_times_is_available(
    service: AvailabilityService, make: Factory
) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    make.member(name="Riley Chen", role=Role.BASS)
    manager = make.manager()

    availability = service.gig_availability(manager, gig.id)

    assert [(p.member.name, p.primary_role, p.busy) for p in availability.players] == [
        ("Riley Chen", Role.BASS, False)
    ]
    assert manager.id not in {p.member.id for p in availability.players}


def test_an_undated_gig_marks_nobody_busy(service: AvailabilityService, make: Factory) -> None:
    gig = make.gig()
    riley = make.member()
    make.busy_time(riley, SOUNDCHECK, END)

    availability = service.gig_availability(make.manager(), gig.id)

    assert (availability.window_starts_at, availability.window_ends_at) == (None, None)
    assert all(p.busy is False for p in availability.players)


def test_members_cant_see_gig_availability(service: AvailabilityService, make: Factory) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)

    with pytest.raises(PermissionDeniedError) as error:
        service.gig_availability(make.member(), gig.id)

    assert error.value.code == "manager_or_band_leader_only"


def test_availability_for_a_missing_gig_is_not_found(
    service: AvailabilityService, make: Factory
) -> None:
    with pytest.raises(NotFoundError) as error:
        service.gig_availability(make.manager(), 9999)

    assert error.value.code == "gig_not_found"

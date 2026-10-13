"""Business rules for gigs, tested through the service with a real (in-memory) database."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleViolation, NotFoundError, PermissionDeniedError
from app.models.enums import ContactLabel, GigStatus, LineupSize, Role, SlotStatus
from app.models.gig import Gig, GigSlot
from app.models.member import Member
from app.schemas.gigs import (
    ContactIn,
    GigCreate,
    GigPage,
    GigSort,
    GigUpdate,
    InvitationIn,
)
from app.services.gigs import GigService
from app.services.lineup import lineup_size
from tests.factories import BLUE_DOOR_FIRST_SET, Factory


@pytest.fixture
def service(db: Session) -> GigService:
    return GigService(db)


def list_for(service: GigService, actor: Member, **filters: Any) -> GigPage:
    params: dict[str, Any] = {
        "q": None,
        "status": None,
        "has_date": None,
        "sort": GigSort.FIRST_SET_AT,
    }
    params.update(filters)
    return service.list_gigs(actor, page=1, page_size=25, **params)


def stored(db: Session, gig: Gig) -> Gig:
    db.expire_all()
    found = db.get(Gig, gig.id)
    assert found is not None
    return found


# ---- Only the manager can change gigs -------------------------------------------------------


def test_manager_can_create_a_gig_with_roles_and_contacts(
    service: GigService, make: Factory
) -> None:
    gig = service.create_gig(
        make.manager(),
        GigCreate(
            venue_name="The Blue Door",
            roles=[Role.RHYTHM_GUITAR_VOCALS, Role.LEAD_GUITAR],
            contacts=[ContactIn(name="Pat Lee", phone="555-0142", notes="Alley door")],
        ),
    )

    assert gig.status is GigStatus.POTENTIAL
    assert [(s.role, s.status) for s in gig.slots] == [
        (Role.RHYTHM_GUITAR_VOCALS, SlotStatus.OPEN),
        (Role.LEAD_GUITAR, SlotStatus.OPEN),
    ]
    assert gig.lineup_size is LineupSize.DUO
    assert [(c.label, c.name, c.notes) for c in gig.contacts] == [
        (ContactLabel.VENUE, "Pat Lee", "Alley door")
    ]


@pytest.mark.parametrize(
    "action",
    [
        lambda s, m, g: s.create_gig(m, GigCreate()),
        lambda s, m, g: s.update_gig(m, g.id, GigUpdate(venue_name="X")),
        lambda s, m, g: s.book_gig(m, g.id),
        lambda s, m, g: s.invite(m, g.id, g.slots[0].id, InvitationIn(member_id=m.id)),
        lambda s, m, g: s.set_slot_pay(m, g.id, g.slots[0].id, 100),
    ],
    ids=["create", "edit", "book", "invite", "set pay"],
)
def test_members_cannot_do_manager_actions(
    service: GigService, make: Factory, db: Session, action: Any
) -> None:
    gig = make.bookable_gig()
    member = make.member()

    with pytest.raises(PermissionDeniedError) as error:
        action(service, member, gig)

    assert error.value.code == "manager_only"


# ---- Booking ----------------------------------------------------------------------------------


def test_complete_gig_with_the_leader_accepted_can_be_booked(
    service: GigService, make: Factory
) -> None:
    gig = make.bookable_gig()

    assert service.book_gig(make.manager(), gig.id).status is GigStatus.BOOKED


def test_booking_an_incomplete_gig_is_refused_and_names_what_is_missing(
    service: GigService, make: Factory, db: Session
) -> None:
    gig = make.bookable_gig(pay_cents=None, venue_address=None)

    with pytest.raises(BusinessRuleViolation) as error:
        service.book_gig(make.manager(), gig.id)

    assert error.value.code == "gig_incomplete"
    assert "venue address" in error.value.detail
    assert "pay" in error.value.detail
    assert stored(db, gig).status is GigStatus.POTENTIAL


def test_booking_an_already_booked_gig_is_an_illegal_transition(
    service: GigService, make: Factory
) -> None:
    gig = make.bookable_gig(status=GigStatus.BOOKED)

    with pytest.raises(BusinessRuleViolation) as error:
        service.book_gig(make.manager(), gig.id)

    assert error.value.code == "gig_not_potential"


def test_booking_a_missing_gig_is_not_found(service: GigService, make: Factory) -> None:
    with pytest.raises(NotFoundError) as error:
        service.book_gig(make.manager(), 9999)

    assert error.value.code == "gig_not_found"


def test_booking_waits_for_every_invited_member_to_accept(
    service: GigService, make: Factory
) -> None:
    gig = make.bookable_gig()
    make.slot(gig, Role.BASS, make.member(role=Role.BASS), SlotStatus.INVITED)

    with pytest.raises(BusinessRuleViolation) as error:
        service.book_gig(make.manager(), gig.id)

    assert error.value.code == "gig_incomplete"
    assert "an accepted member for bass" in error.value.detail


def test_booking_needs_the_band_leader_in_the_lineup(service: GigService, make: Factory) -> None:
    gig = make.bookable_gig(leader=make.member(role=Role.RHYTHM_GUITAR_VOCALS, leader=False))

    with pytest.raises(BusinessRuleViolation) as error:
        service.book_gig(make.manager(), gig.id)

    assert "the band leader, accepted into the lineup" in error.value.detail


def test_a_contact_without_phone_or_email_does_not_count(
    service: GigService, make: Factory
) -> None:
    gig = make.gig(**{"first_set_at": BLUE_DOOR_FIRST_SET})
    make.contact(gig, name="Pat Lee", notes="Ask at the bar")

    detail = service.get_gig(make.manager(), gig.id)

    assert "a contact with a name and a phone number or email" in detail.missing_for_booking


def test_missing_for_booking_lists_every_gap_for_an_empty_draft(
    service: GigService, make: Factory
) -> None:
    detail = service.create_gig(make.manager(), GigCreate())

    assert detail.missing_for_booking == [
        "first set date and time",
        "venue name",
        "venue address",
        "pay",
        "a contact with a name and a phone number or email",
        "at least one role in the lineup",
        "the band leader, accepted into the lineup",
    ]


# ---- Editing ----------------------------------------------------------------------------------


def test_editing_changes_only_the_fields_sent(service: GigService, make: Factory) -> None:
    gig = make.bookable_gig()

    updated = service.update_gig(make.manager(), gig.id, GigUpdate(pay_cents=55_000))

    assert updated.pay_cents == 55_000
    assert updated.venue_name == "The Blue Door"
    assert len(updated.contacts) == 1


def test_sending_null_clears_a_field(service: GigService, make: Factory) -> None:
    gig = make.bookable_gig()

    assert (
        service.update_gig(make.manager(), gig.id, GigUpdate(venue_address=None)).venue_address
        is None
    )


def test_null_lengths_reset_to_their_defaults(service: GigService, make: Factory) -> None:
    gig = make.bookable_gig(load_in_offset_minutes=180, performance_minutes=90)

    updated = service.update_gig(
        make.manager(),
        gig.id,
        GigUpdate(load_in_offset_minutes=None, performance_minutes=None),
    )

    assert (updated.load_in_offset_minutes, updated.performance_minutes) == (120, 180)


def test_times_sent_with_any_time_zone_are_returned_in_utc(
    service: GigService, make: Factory
) -> None:
    eastern = timezone(timedelta(hours=-4))

    detail = service.create_gig(
        make.manager(), GigCreate(first_set_at=datetime(2026, 10, 18, 20, 0, tzinfo=eastern))
    )

    assert detail.first_set_at == BLUE_DOOR_FIRST_SET
    assert detail.first_set_at is not None
    assert detail.first_set_at.utcoffset() == timedelta(0)


def test_contacts_are_replaced_as_a_list(service: GigService, make: Factory) -> None:
    gig = make.bookable_gig()

    updated = service.update_gig(
        make.manager(),
        gig.id,
        GigUpdate(
            contacts=[
                ContactIn(label=ContactLabel.BOOKING, name="Morgan Hale", email="m@example.com"),
                ContactIn(label=ContactLabel.OTHER, notes="Sound person: ask for Lee"),
            ]
        ),
    )

    assert [(c.label, c.name) for c in updated.contacts] == [
        (ContactLabel.BOOKING, "Morgan Hale"),
        (ContactLabel.OTHER, None),
    ]


def test_changing_roles_keeps_invitations_for_roles_that_stay(
    service: GigService, make: Factory
) -> None:
    gig = make.bookable_gig()
    make.slot(gig, Role.DRUMS)

    updated = service.update_gig(
        make.manager(), gig.id, GigUpdate(roles=[Role.RHYTHM_GUITAR_VOCALS, Role.BASS])
    )

    assert [(s.role, s.status) for s in updated.slots] == [
        (Role.RHYTHM_GUITAR_VOCALS, SlotStatus.ACCEPTED),
        (Role.BASS, SlotStatus.OPEN),
    ]


def test_a_booked_gig_can_be_edited_while_it_stays_complete(
    service: GigService, make: Factory
) -> None:
    gig = make.bookable_gig(status=GigStatus.BOOKED)

    updated = service.update_gig(make.manager(), gig.id, GigUpdate(pay_cents=60_000))

    assert (updated.pay_cents, updated.status) == (60_000, GigStatus.BOOKED)


@pytest.mark.parametrize(
    "update",
    [
        GigUpdate(pay_cents=None),
        GigUpdate(roles=[Role.RHYTHM_GUITAR_VOCALS, Role.DRUMS]),
        GigUpdate(contacts=[]),
    ],
    ids=["clear pay", "add an unfilled role", "remove every contact"],
)
def test_a_booked_gig_cannot_be_left_incomplete(
    service: GigService, make: Factory, db: Session, update: GigUpdate
) -> None:
    gig = make.bookable_gig(status=GigStatus.BOOKED)

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_gig(make.manager(), gig.id, update)

    assert error.value.code == "gig_incomplete"
    unchanged = stored(db, gig)
    assert unchanged.pay_cents == 40_000
    assert [s.role for s in unchanged.slots] == [Role.RHYTHM_GUITAR_VOCALS]
    assert len(unchanged.contacts) == 1


def test_editing_a_missing_gig_is_not_found(service: GigService, make: Factory) -> None:
    with pytest.raises(NotFoundError) as error:
        service.update_gig(make.manager(), 9999, GigUpdate(pay_cents=1))

    assert error.value.code == "gig_not_found"


# ---- Derived values -----------------------------------------------------------------------


def test_load_in_soundcheck_and_end_are_computed_from_the_first_set(
    service: GigService, make: Factory
) -> None:
    gig = make.bookable_gig(
        load_in_offset_minutes=120, soundcheck_offset_minutes=75, performance_minutes=150
    )

    detail = service.get_gig(make.manager(), gig.id)

    assert detail.load_in_at == BLUE_DOOR_FIRST_SET - timedelta(hours=2)
    assert detail.soundcheck_at == BLUE_DOOR_FIRST_SET - timedelta(minutes=75)
    assert detail.end_at == BLUE_DOOR_FIRST_SET + timedelta(minutes=150)


def test_moving_the_first_set_moves_every_time_without_storing_them(
    service: GigService, make: Factory, db: Session
) -> None:
    gig = make.bookable_gig(load_in_offset_minutes=120, soundcheck_offset_minutes=75)
    later = BLUE_DOOR_FIRST_SET + timedelta(hours=1)

    detail = service.update_gig(make.manager(), gig.id, GigUpdate(first_set_at=later))

    assert detail.load_in_at == later - timedelta(hours=2)
    assert detail.soundcheck_at == later - timedelta(minutes=75)
    assert detail.end_at == later + timedelta(minutes=180)
    columns = {column.key for column in inspect(Gig).columns}
    assert columns.isdisjoint({"load_in_at", "soundcheck_at", "end_at", "lineup_size"})
    kept = stored(db, gig)
    assert (kept.load_in_offset_minutes, kept.soundcheck_offset_minutes) == (120, 75)


def test_an_undated_gig_has_no_times(service: GigService, make: Factory) -> None:
    gig = make.gig(venue_name="Wedding inquiry")

    detail = service.get_gig(make.manager(), gig.id)

    assert (detail.load_in_at, detail.soundcheck_at, detail.end_at) == (None, None, None)


@pytest.mark.parametrize(
    ("count", "size"),
    [
        (0, None),
        (1, LineupSize.SOLO),
        (2, LineupSize.DUO),
        (3, LineupSize.TRIO),
        (4, LineupSize.QUARTET),
        (5, LineupSize.FULL_BAND),
    ],
)
def test_lineup_size_comes_from_the_number_of_roles(count: int, size: LineupSize | None) -> None:
    assert lineup_size(count) is size


def test_lineup_size_follows_role_changes(service: GigService, make: Factory) -> None:
    gig = make.bookable_gig()
    manager = make.manager()

    assert service.get_gig(manager, gig.id).lineup_size is LineupSize.SOLO
    updated = service.update_gig(
        manager, gig.id, GigUpdate(roles=[Role.RHYTHM_GUITAR_VOCALS, Role.BASS, Role.DRUMS])
    )
    assert updated.lineup_size is LineupSize.TRIO


# ---- Invitations --------------------------------------------------------------------------


def test_manager_invites_a_member_with_their_pay(service: GigService, make: Factory) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS)
    riley = make.member(name="Riley Chen", role=Role.BASS)

    detail = service.invite(
        make.manager(), gig.id, slot.id, InvitationIn(member_id=riley.id, pay_cents=15_000)
    )

    invited = detail.slots[0]
    assert invited.status is SlotStatus.INVITED
    assert invited.member is not None and invited.member.name == "Riley Chen"
    assert invited.pay_cents == 15_000


def test_a_member_outside_the_role_can_be_invited_as_a_backup(
    service: GigService, make: Factory
) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS)
    guitarist = make.member(role=Role.LEAD_GUITAR)

    detail = service.invite(make.manager(), gig.id, slot.id, InvitationIn(member_id=guitarist.id))

    assert detail.slots[0].status is SlotStatus.INVITED


def test_after_a_decline_the_manager_can_invite_a_backup(
    service: GigService, make: Factory
) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, make.member(), SlotStatus.DECLINED)
    backup = make.member(name="Backup Bassist")

    detail = service.invite(make.manager(), gig.id, slot.id, InvitationIn(member_id=backup.id))

    assert detail.slots[0].member is not None
    assert detail.slots[0].member.name == "Backup Bassist"
    assert detail.slots[0].status is SlotStatus.INVITED
    assert detail.slots[0].responded_at is None


@pytest.mark.parametrize(
    ("setup", "code"),
    [
        ("accepted", "slot_already_filled"),
        ("unknown member", "unknown_member"),
        ("manager", "manager_cannot_play"),
        ("already on gig", "member_in_two_slots"),
        ("booked", "gig_not_potential"),
    ],
)
def test_invitations_that_break_a_rule_are_refused(
    service: GigService, make: Factory, setup: str, code: str
) -> None:
    manager = make.manager()
    gig = make.gig(status=GigStatus.BOOKED if setup == "booked" else GigStatus.POTENTIAL)
    member = make.member()
    slot = make.slot(
        gig,
        Role.BASS,
        make.member() if setup == "accepted" else None,
        SlotStatus.ACCEPTED if setup == "accepted" else None,
    )
    if setup == "already on gig":
        make.slot(gig, Role.DRUMS, member)
    member_id = {"unknown member": 9999, "manager": manager.id}.get(setup, member.id)

    with pytest.raises(BusinessRuleViolation) as error:
        service.invite(manager, gig.id, slot.id, InvitationIn(member_id=member_id))

    assert error.value.code == code


def test_inviting_to_a_slot_on_another_gig_is_not_found(service: GigService, make: Factory) -> None:
    gig = make.gig()
    other_slot = make.slot(make.gig(), Role.BASS)

    with pytest.raises(NotFoundError) as error:
        service.invite(make.manager(), gig.id, other_slot.id, InvitationIn(member_id=1))

    assert error.value.code == "slot_not_found"


def test_manager_can_change_a_members_pay(service: GigService, make: Factory) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, make.member(), pay_cents=10_000)

    detail = service.set_slot_pay(make.manager(), gig.id, slot.id, 12_500)

    assert detail.slots[0].pay_cents == 12_500


# ---- Answering invitations ----------------------------------------------------------------


def test_invited_member_can_accept(service: GigService, make: Factory) -> None:
    riley = make.member()
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    slot = make.slot(gig, Role.BASS, riley)

    detail = service.accept(riley, gig.id, slot.id)

    assert detail.slots[0].status is SlotStatus.ACCEPTED
    assert detail.slots[0].responded_at is not None


def test_invited_member_can_decline(service: GigService, make: Factory) -> None:
    riley = make.member()
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, riley)

    assert service.decline(riley, gig.id, slot.id).slots[0].status is SlotStatus.DECLINED


def test_a_member_cannot_answer_someone_elses_invitation(
    service: GigService, make: Factory
) -> None:
    riley, taylor = make.member(), make.member(role=Role.DRUMS)
    gig = make.gig()
    make.slot(gig, Role.DRUMS, taylor)
    riley_slot = make.slot(gig, Role.BASS, riley)

    with pytest.raises(PermissionDeniedError) as error:
        service.accept(taylor, gig.id, riley_slot.id)

    assert error.value.code == "not_your_invitation"


def test_a_member_with_no_slot_cannot_tell_the_gig_exists(
    service: GigService, make: Factory
) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, make.member())

    with pytest.raises(NotFoundError) as error:
        service.accept(make.member(), gig.id, slot.id)

    assert error.value.code == "gig_not_found"


@pytest.mark.parametrize("answer", ["accept", "decline"])
def test_an_invitation_can_only_be_answered_once(
    service: GigService, make: Factory, answer: str
) -> None:
    riley = make.member()
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, riley, SlotStatus.DECLINED)

    with pytest.raises(BusinessRuleViolation) as error:
        getattr(service, answer)(riley, gig.id, slot.id)

    assert error.value.code == "invitation_not_pending"


# ---- No double-confirming -----------------------------------------------------------------


def test_accepting_a_gig_that_overlaps_one_already_accepted_is_refused(
    service: GigService, make: Factory, db: Session
) -> None:
    riley = make.member()
    evening = make.gig(venue_name="The Blue Door", first_set_at=BLUE_DOOR_FIRST_SET)
    make.slot(evening, Role.BASS, riley, SlotStatus.ACCEPTED)
    # Starts during the Blue Door gig's three-hour set.
    clash = make.gig(first_set_at=BLUE_DOOR_FIRST_SET + timedelta(hours=2))
    slot = make.slot(clash, Role.BASS, riley)

    with pytest.raises(BusinessRuleViolation) as error:
        service.accept(riley, clash.id, slot.id)

    assert error.value.code == "overlapping_gig"
    assert "The Blue Door" in error.value.detail
    db.expire_all()
    assert db.get(GigSlot, slot.id).status is SlotStatus.INVITED  # type: ignore[union-attr]


def test_a_morning_and_an_evening_gig_can_both_be_accepted(
    service: GigService, make: Factory
) -> None:
    riley = make.member()
    evening = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    make.slot(evening, Role.BASS, riley, SlotStatus.ACCEPTED)
    morning = make.gig(first_set_at=BLUE_DOOR_FIRST_SET - timedelta(hours=10))
    slot = make.slot(morning, Role.BASS, riley)

    assert service.accept(riley, morning.id, slot.id).slots[0].status is SlotStatus.ACCEPTED


def test_load_in_counts_toward_the_overlap(service: GigService, make: Factory) -> None:
    riley = make.member()
    earlier = make.gig(first_set_at=BLUE_DOOR_FIRST_SET - timedelta(hours=4))  # ends 1h before
    make.slot(earlier, Role.BASS, riley, SlotStatus.ACCEPTED)
    later = make.gig(first_set_at=BLUE_DOOR_FIRST_SET, load_in_offset_minutes=120)
    slot = make.slot(later, Role.BASS, riley)

    with pytest.raises(BusinessRuleViolation) as error:
        service.accept(riley, later.id, slot.id)

    assert error.value.code == "overlapping_gig"


def test_cancelled_and_undated_gigs_never_overlap(service: GigService, make: Factory) -> None:
    riley = make.member()
    cancelled = make.gig(status=GigStatus.CANCELLED, first_set_at=BLUE_DOOR_FIRST_SET)
    make.slot(cancelled, Role.BASS, riley, SlotStatus.ACCEPTED)
    undated = make.gig()
    make.slot(undated, Role.DRUMS, riley, SlotStatus.ACCEPTED)
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    slot = make.slot(gig, Role.BASS, riley)

    assert service.accept(riley, gig.id, slot.id).slots[0].status is SlotStatus.ACCEPTED


def test_moving_a_gig_onto_a_members_other_gig_is_refused(
    service: GigService, make: Factory, db: Session
) -> None:
    riley = make.member(name="Riley Chen")
    other = make.gig(venue_name="Hub City Tap", first_set_at=BLUE_DOOR_FIRST_SET)
    make.slot(other, Role.BASS, riley, SlotStatus.ACCEPTED)
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET + timedelta(days=1))
    make.slot(gig, Role.BASS, riley, SlotStatus.ACCEPTED)

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_gig(make.manager(), gig.id, GigUpdate(first_set_at=BLUE_DOOR_FIRST_SET))

    assert error.value.code == "overlapping_gig"
    assert "Riley Chen" in error.value.detail
    assert stored(db, gig).first_set_at == BLUE_DOOR_FIRST_SET + timedelta(days=1)


# ---- What members can see -----------------------------------------------------------------


def test_an_invited_member_sees_the_potential_gig_and_only_their_own_pay(
    service: GigService, make: Factory
) -> None:
    gig = make.bookable_gig()
    riley = make.member()
    make.slot(gig, Role.BASS, riley, pay_cents=15_000)

    detail = service.get_gig(riley, gig.id)

    assert detail.pay_cents is None
    pay_by_role = {slot.role: slot.pay_cents for slot in detail.slots}
    assert pay_by_role == {Role.RHYTHM_GUITAR_VOCALS: None, Role.BASS: 15_000}
    assert detail.my_slot_id == next(s.id for s in detail.slots if s.role is Role.BASS)
    assert detail.missing_for_booking == []


def test_the_manager_sees_every_pay(service: GigService, make: Factory) -> None:
    gig = make.bookable_gig()

    detail = service.get_gig(make.manager(), gig.id)

    assert detail.pay_cents == 40_000
    assert detail.slots[0].pay_cents == 20_000
    assert detail.my_slot_id is None


@pytest.mark.parametrize("slot_status", [None, SlotStatus.DECLINED])
def test_a_potential_gig_looks_missing_to_members_who_arent_invited(
    service: GigService, make: Factory, slot_status: SlotStatus | None
) -> None:
    gig = make.bookable_gig()
    member = make.member()
    if slot_status:
        make.slot(gig, Role.BASS, member, slot_status)

    with pytest.raises(NotFoundError) as error:
        service.get_gig(member, gig.id)

    assert error.value.code == "gig_not_found"


def test_a_member_in_the_lineup_sees_the_booked_gig(service: GigService, make: Factory) -> None:
    leader = make.leader()
    gig = make.bookable_gig(status=GigStatus.BOOKED, leader=leader)

    assert service.get_gig(leader, gig.id).venue_name == "The Blue Door"


def test_a_member_not_in_the_lineup_cannot_open_a_booked_gig(
    service: GigService, make: Factory
) -> None:
    gig = make.bookable_gig(status=GigStatus.BOOKED)

    with pytest.raises(PermissionDeniedError) as error:
        service.get_gig(make.member(), gig.id)

    assert error.value.code == "not_assigned_to_gig"


def test_members_list_booked_gigs_and_their_invitations(service: GigService, make: Factory) -> None:
    riley = make.member()
    mine = make.bookable_gig(status=GigStatus.BOOKED, venue_name="Mine")
    make.slot(mine, Role.BASS, riley, SlotStatus.ACCEPTED)
    not_mine = make.bookable_gig(status=GigStatus.BOOKED, venue_name="Not mine")
    invited = make.gig(venue_name="Invited", first_set_at=BLUE_DOOR_FIRST_SET)
    make.slot(invited, Role.BASS, riley)
    make.gig(venue_name="Draft I'm not on")

    page = list_for(service, riley)

    rows = {row.id: row for row in page.items}
    assert set(rows) == {mine.id, not_mine.id, invited.id}
    assert (rows[mine.id].restricted, rows[mine.id].my_slot_status) == (
        False,
        SlotStatus.ACCEPTED,
    )
    assert rows[invited.id].my_slot_status is SlotStatus.INVITED
    assert rows[invited.id].venue_name == "Invited"
    assert rows[not_mine.id].restricted is True
    assert rows[not_mine.id].venue_name is None
    assert rows[not_mine.id].lineup_size is None


def test_member_search_never_matches_restricted_gigs(service: GigService, make: Factory) -> None:
    make.bookable_gig(status=GigStatus.BOOKED, venue_name="Secret Venue")

    assert list_for(service, make.member(), q="Secret").total == 0


def test_member_filtering_to_potential_gigs_gets_only_invitations(
    service: GigService, make: Factory
) -> None:
    riley = make.member()
    invited = make.gig()
    make.slot(invited, Role.BASS, riley)
    make.gig()

    page = list_for(service, riley, status=GigStatus.POTENTIAL)

    assert [row.id for row in page.items] == [invited.id]


def test_manager_lists_every_gig_with_details(service: GigService, make: Factory) -> None:
    make.bookable_gig(status=GigStatus.BOOKED)
    make.gig(venue_name="Draft")

    page = list_for(service, make.manager())

    assert page.total == 2
    assert all(row.restricted is False and row.my_slot_status is None for row in page.items)


def test_manager_can_filter_by_status(service: GigService, make: Factory) -> None:
    make.bookable_gig(status=GigStatus.BOOKED)
    draft = make.gig(venue_name="Draft")

    page = list_for(service, make.manager(), status=GigStatus.POTENTIAL)

    assert [row.id for row in page.items] == [draft.id]

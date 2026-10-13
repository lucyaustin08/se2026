"""Business rules for gigs, tested through the service with a real (in-memory) database."""

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleViolation, NotFoundError, PermissionDeniedError
from app.models.enums import GigStatus, GigType, Role
from app.models.gig import Gig, GigAssignment
from app.models.member import Member
from app.schemas.gigs import (
    ContactIn,
    GigCreate,
    GigPage,
    GigSort,
    GigUpdate,
    LineupAssignmentIn,
)
from app.services.gigs import GigService
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


# ---- Only the manager can change gigs -------------------------------------------------------


def test_manager_can_create_a_gig_as_potential(service: GigService, make: Factory) -> None:
    manager = make.manager()

    gig = service.create_gig(manager, GigCreate(venue_name="The Blue Door"))

    assert gig.status is GigStatus.POTENTIAL
    assert gig.venue_name == "The Blue Door"


def test_member_cannot_create_a_gig(service: GigService, make: Factory, db: Session) -> None:
    member = make.member()

    with pytest.raises(PermissionDeniedError) as error:
        service.create_gig(member, GigCreate(venue_name="The Blue Door"))

    assert error.value.code == "manager_only"
    assert db.scalars(select(Gig)).all() == []


def test_member_cannot_edit_a_gig(service: GigService, make: Factory) -> None:
    gig = make.gig(venue_name="The Blue Door")

    with pytest.raises(PermissionDeniedError) as error:
        service.update_gig(make.member(), gig.id, GigUpdate(venue_name="Somewhere else"))

    assert error.value.code == "manager_only"


def test_member_cannot_book_a_gig(service: GigService, make: Factory) -> None:
    gig = make.complete_gig()

    with pytest.raises(PermissionDeniedError) as error:
        service.book_gig(make.member(), gig.id)

    assert error.value.code == "manager_only"


# ---- Booking ----------------------------------------------------------------------------------


def test_complete_potential_gig_can_be_booked(service: GigService, make: Factory) -> None:
    gig = make.complete_gig()

    booked = service.book_gig(make.manager(), gig.id)

    assert booked.status is GigStatus.BOOKED


def test_booking_an_incomplete_gig_is_refused_and_names_what_is_missing(
    service: GigService, make: Factory, db: Session
) -> None:
    gig = make.complete_gig(pay_cents=None, venue_address=None)

    with pytest.raises(BusinessRuleViolation) as error:
        service.book_gig(make.manager(), gig.id)

    assert error.value.code == "gig_incomplete"
    assert "venue address" in error.value.detail
    assert "pay" in error.value.detail
    db.refresh(gig)
    assert gig.status is GigStatus.POTENTIAL


def test_booking_an_already_booked_gig_is_an_illegal_transition(
    service: GigService, make: Factory
) -> None:
    gig = make.complete_gig(status=GigStatus.BOOKED)

    with pytest.raises(BusinessRuleViolation) as error:
        service.book_gig(make.manager(), gig.id)

    assert error.value.code == "gig_not_potential"


def test_booking_a_missing_gig_is_not_found(service: GigService, make: Factory) -> None:
    with pytest.raises(NotFoundError) as error:
        service.book_gig(make.manager(), 9999)

    assert error.value.code == "gig_not_found"


def test_a_contact_without_phone_or_email_does_not_count(
    service: GigService, make: Factory
) -> None:
    gig = make.complete_gig(venue_contact_phone=None)

    with pytest.raises(BusinessRuleViolation) as error:
        service.book_gig(make.manager(), gig.id)

    assert error.value.code == "gig_incomplete"
    assert "a contact with a name and a phone number or email" in error.value.detail


def test_a_booking_contact_with_email_satisfies_the_contact_rule(
    service: GigService, make: Factory
) -> None:
    gig = make.complete_gig(
        venue_contact_name=None,
        venue_contact_phone=None,
        booking_contact_name="Morgan Hale",
        booking_contact_email="morgan@example.com",
    )

    booked = service.book_gig(make.manager(), gig.id)

    assert booked.status is GigStatus.BOOKED


def test_missing_for_booking_lists_every_gap_for_an_empty_draft(
    service: GigService, make: Factory
) -> None:
    detail = service.create_gig(make.manager(), GigCreate())

    assert detail.missing_for_booking == [
        "first set date and time",
        "venue name",
        "venue address",
        "gig type",
        "pay",
        "a contact with a name and a phone number or email",
    ]


# ---- Editing ----------------------------------------------------------------------------------


def test_editing_changes_only_the_fields_sent(service: GigService, make: Factory) -> None:
    gig = make.complete_gig()

    updated = service.update_gig(make.manager(), gig.id, GigUpdate(pay_cents=55_000))

    assert updated.pay_cents == 55_000
    assert updated.venue_name == "The Blue Door"
    assert updated.first_set_at == BLUE_DOOR_FIRST_SET


def test_sending_null_clears_a_field(service: GigService, make: Factory) -> None:
    gig = make.complete_gig()

    updated = service.update_gig(make.manager(), gig.id, GigUpdate(venue_address=None))

    assert updated.venue_address is None


def test_null_offset_resets_to_the_default(service: GigService, make: Factory) -> None:
    gig = make.complete_gig(load_in_offset_minutes=180)

    updated = service.update_gig(make.manager(), gig.id, GigUpdate(load_in_offset_minutes=None))

    assert updated.load_in_offset_minutes == 120


def test_contacts_can_be_replaced_and_cleared(service: GigService, make: Factory) -> None:
    gig = make.complete_gig()
    manager = make.manager()

    updated = service.update_gig(
        manager,
        gig.id,
        GigUpdate(booking_contact=ContactIn(name="Morgan Hale", email="morgan@example.com")),
    )
    assert updated.booking_contact is not None
    assert updated.booking_contact.email == "morgan@example.com"

    cleared = service.update_gig(manager, gig.id, GigUpdate(booking_contact=None))
    assert cleared.booking_contact is None


def test_a_booked_gig_can_be_edited_while_it_stays_complete(
    service: GigService, make: Factory
) -> None:
    gig = make.complete_gig(status=GigStatus.BOOKED)

    updated = service.update_gig(make.manager(), gig.id, GigUpdate(pay_cents=60_000))

    assert updated.pay_cents == 60_000
    assert updated.status is GigStatus.BOOKED


def test_a_booked_gig_cannot_lose_a_required_field(
    service: GigService, make: Factory, db: Session
) -> None:
    gig = make.complete_gig(status=GigStatus.BOOKED)

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_gig(make.manager(), gig.id, GigUpdate(pay_cents=None))

    assert error.value.code == "gig_incomplete"
    db.expire_all()
    assert db.get(Gig, gig.id).pay_cents == 40_000  # type: ignore[union-attr]


def test_editing_a_missing_gig_is_not_found(service: GigService, make: Factory) -> None:
    with pytest.raises(NotFoundError) as error:
        service.update_gig(make.manager(), 9999, GigUpdate(pay_cents=1))

    assert error.value.code == "gig_not_found"


# ---- Derived day-of times -----------------------------------------------------------------


def test_load_in_and_soundcheck_are_computed_from_the_first_set(
    service: GigService, make: Factory
) -> None:
    gig = make.complete_gig(load_in_offset_minutes=120, soundcheck_offset_minutes=75)

    detail = service.get_gig(make.manager(), gig.id)

    assert detail.load_in_at == BLUE_DOOR_FIRST_SET - timedelta(hours=2)
    assert detail.soundcheck_at == BLUE_DOOR_FIRST_SET - timedelta(minutes=75)


def test_moving_the_first_set_moves_load_in_and_soundcheck_without_storing_them(
    service: GigService, make: Factory, db: Session
) -> None:
    gig = make.complete_gig(load_in_offset_minutes=120, soundcheck_offset_minutes=75)
    one_hour_later = BLUE_DOOR_FIRST_SET + timedelta(hours=1)

    detail = service.update_gig(make.manager(), gig.id, GigUpdate(first_set_at=one_hour_later))

    assert detail.load_in_at == one_hour_later - timedelta(hours=2)
    assert detail.soundcheck_at == one_hour_later - timedelta(minutes=75)
    # Only the offsets are stored, and they did not change.
    columns = {column.key for column in inspect(Gig).columns}
    assert "load_in_at" not in columns
    assert "soundcheck_at" not in columns
    db.expire_all()
    stored = db.get(Gig, gig.id)
    assert stored is not None
    assert (stored.load_in_offset_minutes, stored.soundcheck_offset_minutes) == (120, 75)


def test_an_undated_gig_has_no_day_of_times(service: GigService, make: Factory) -> None:
    gig = make.gig(venue_name="Wedding inquiry")

    detail = service.get_gig(make.manager(), gig.id)

    assert (detail.first_set_at, detail.load_in_at, detail.soundcheck_at) == (None, None, None)


# ---- Lineup -----------------------------------------------------------------------------------


def test_lineup_shows_every_slot_of_the_gig_type(service: GigService, make: Factory) -> None:
    gig = make.complete_gig(gig_type=GigType.FULL_BAND)

    detail = service.get_gig(make.manager(), gig.id)

    assert [slot.slot for slot in detail.lineup] == [
        Role.RHYTHM_GUITAR_VOCALS,
        Role.LEAD_GUITAR,
        Role.BASS,
        Role.DRUMS,
        Role.SPECIALTY,
    ]
    assert all(slot.member is None for slot in detail.lineup)


def test_trio_offers_only_its_two_fixed_slots_for_now(service: GigService, make: Factory) -> None:
    gig = make.complete_gig(gig_type=GigType.TRIO)

    detail = service.get_gig(make.manager(), gig.id)

    assert [slot.slot for slot in detail.lineup] == [Role.RHYTHM_GUITAR_VOCALS, Role.LEAD_GUITAR]


def test_manager_can_assign_members_matching_their_roles(
    service: GigService, make: Factory
) -> None:
    gig = make.complete_gig(gig_type=GigType.DUO)
    sam = make.member(name="Sam Rivera", role=Role.RHYTHM_GUITAR_VOCALS)
    casey = make.member(name="Casey Morgan", role=Role.LEAD_GUITAR)

    detail = service.update_gig(
        make.manager(),
        gig.id,
        GigUpdate(
            lineup=[
                LineupAssignmentIn(slot=Role.RHYTHM_GUITAR_VOCALS, member_id=sam.id),
                LineupAssignmentIn(slot=Role.LEAD_GUITAR, member_id=casey.id),
            ]
        ),
    )

    assert [(s.slot, s.member.name if s.member else None) for s in detail.lineup] == [
        (Role.RHYTHM_GUITAR_VOCALS, "Sam Rivera"),
        (Role.LEAD_GUITAR, "Casey Morgan"),
    ]


def test_reassigning_a_slot_replaces_the_previous_member(
    service: GigService, make: Factory, db: Session
) -> None:
    gig = make.complete_gig(gig_type=GigType.DUO)
    first = make.member(name="First Lead", role=Role.LEAD_GUITAR)
    second = make.member(name="Second Lead", role=Role.LEAD_GUITAR)
    make.assign(gig, first, Role.LEAD_GUITAR)

    detail = service.update_gig(
        make.manager(),
        gig.id,
        GigUpdate(lineup=[LineupAssignmentIn(slot=Role.LEAD_GUITAR, member_id=second.id)]),
    )

    lead = next(s for s in detail.lineup if s.slot is Role.LEAD_GUITAR)
    assert lead.member is not None
    assert lead.member.name == "Second Lead"
    assert len(db.scalars(select(GigAssignment)).all()) == 1


def test_an_empty_lineup_clears_every_slot(service: GigService, make: Factory) -> None:
    gig = make.complete_gig(gig_type=GigType.DUO)
    make.assign(gig, make.member(role=Role.LEAD_GUITAR), Role.LEAD_GUITAR)

    detail = service.update_gig(make.manager(), gig.id, GigUpdate(lineup=[]))

    assert all(slot.member is None for slot in detail.lineup)


@pytest.mark.parametrize(
    ("gig_type", "slot", "role", "code"),
    [
        (GigType.DUO, Role.BASS, Role.BASS, "slot_not_in_lineup"),
        (GigType.DUO, Role.LEAD_GUITAR, Role.BASS, "member_role_mismatch"),
        (None, Role.LEAD_GUITAR, Role.LEAD_GUITAR, "gig_type_required"),
    ],
)
def test_lineup_assignments_that_break_a_rule_are_refused(
    service: GigService,
    make: Factory,
    gig_type: GigType | None,
    slot: Role,
    role: Role,
    code: str,
) -> None:
    gig = make.complete_gig(gig_type=gig_type)
    member = make.member(role=role)

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_gig(
            make.manager(),
            gig.id,
            GigUpdate(lineup=[LineupAssignmentIn(slot=slot, member_id=member.id)]),
        )

    assert error.value.code == code


def test_an_unknown_member_cannot_be_assigned(service: GigService, make: Factory) -> None:
    gig = make.complete_gig(gig_type=GigType.DUO)

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_gig(
            make.manager(),
            gig.id,
            GigUpdate(lineup=[LineupAssignmentIn(slot=Role.LEAD_GUITAR, member_id=9999)]),
        )

    assert error.value.code == "unknown_member"


def test_one_slot_cannot_be_given_two_members(service: GigService, make: Factory) -> None:
    gig = make.complete_gig(gig_type=GigType.DUO)
    a = make.member(role=Role.LEAD_GUITAR)
    b = make.member(role=Role.LEAD_GUITAR)

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_gig(
            make.manager(),
            gig.id,
            GigUpdate(
                lineup=[
                    LineupAssignmentIn(slot=Role.LEAD_GUITAR, member_id=a.id),
                    LineupAssignmentIn(slot=Role.LEAD_GUITAR, member_id=b.id),
                ]
            ),
        )

    assert error.value.code == "duplicate_slot"


def test_one_member_cannot_fill_two_slots(service: GigService, make: Factory) -> None:
    gig = make.complete_gig(gig_type=GigType.DUO)
    member = make.member(role=Role.LEAD_GUITAR)

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_gig(
            make.manager(),
            gig.id,
            GigUpdate(
                lineup=[
                    LineupAssignmentIn(slot=Role.LEAD_GUITAR, member_id=member.id),
                    LineupAssignmentIn(slot=Role.RHYTHM_GUITAR_VOCALS, member_id=member.id),
                ]
            ),
        )

    assert error.value.code == "member_in_two_slots"


def test_changing_gig_type_is_refused_when_assigned_slots_would_disappear(
    service: GigService, make: Factory, db: Session
) -> None:
    gig = make.complete_gig(gig_type=GigType.FULL_BAND)
    make.assign(gig, make.member(role=Role.BASS), Role.BASS)

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_gig(make.manager(), gig.id, GigUpdate(gig_type=GigType.DUO))

    assert error.value.code == "lineup_not_in_gig_type"
    db.expire_all()
    assert db.get(Gig, gig.id).gig_type is GigType.FULL_BAND  # type: ignore[union-attr]


def test_changing_gig_type_with_a_fitting_lineup_is_allowed(
    service: GigService, make: Factory
) -> None:
    gig = make.complete_gig(gig_type=GigType.FULL_BAND)
    make.assign(gig, make.member(role=Role.BASS), Role.BASS)

    detail = service.update_gig(make.manager(), gig.id, GigUpdate(gig_type=GigType.DUO, lineup=[]))

    assert detail.gig_type is GigType.DUO


# ---- What members can see ---------------------------------------------------------------------


def test_assigned_member_sees_a_booked_gig_without_pay(service: GigService, make: Factory) -> None:
    gig = make.complete_gig(status=GigStatus.BOOKED)
    member = make.member(role=Role.LEAD_GUITAR)
    make.assign(gig, member, Role.LEAD_GUITAR)

    detail = service.get_gig(member, gig.id)

    assert detail.venue_name == "The Blue Door"
    assert detail.pay_cents is None
    assert detail.missing_for_booking == []


def test_manager_sees_pay(service: GigService, make: Factory) -> None:
    gig = make.complete_gig(status=GigStatus.BOOKED)

    assert service.get_gig(make.manager(), gig.id).pay_cents == 40_000


def test_unassigned_member_cannot_open_a_booked_gig(service: GigService, make: Factory) -> None:
    gig = make.complete_gig(status=GigStatus.BOOKED)

    with pytest.raises(PermissionDeniedError) as error:
        service.get_gig(make.member(), gig.id)

    assert error.value.code == "not_assigned_to_gig"


def test_a_potential_gig_looks_missing_to_members(service: GigService, make: Factory) -> None:
    gig = make.complete_gig()
    member = make.member(role=Role.LEAD_GUITAR)
    make.assign(gig, member, Role.LEAD_GUITAR)

    with pytest.raises(NotFoundError) as error:
        service.get_gig(member, gig.id)

    assert error.value.code == "gig_not_found"


def test_members_list_only_booked_gigs_and_unassigned_ones_are_restricted(
    service: GigService, make: Factory
) -> None:
    member = make.member(role=Role.LEAD_GUITAR)
    mine = make.complete_gig(status=GigStatus.BOOKED, venue_name="Mine")
    make.assign(mine, member, Role.LEAD_GUITAR)
    make.complete_gig(status=GigStatus.BOOKED, venue_name="Not mine")
    make.complete_gig(status=GigStatus.POTENTIAL, venue_name="Potential")

    page = list_for(service, member)

    assert page.total == 2
    rows = {row.id: row for row in page.items}
    assert rows[mine.id].restricted is False
    assert rows[mine.id].venue_name == "Mine"
    other = next(row for row in page.items if row.id != mine.id)
    assert other.restricted is True
    assert other.venue_name is None
    assert other.gig_type is None
    assert other.first_set_at == BLUE_DOOR_FIRST_SET


def test_member_search_never_matches_restricted_gigs(service: GigService, make: Factory) -> None:
    member = make.member(role=Role.LEAD_GUITAR)
    make.complete_gig(status=GigStatus.BOOKED, venue_name="Secret Venue")

    page = list_for(service, member, q="Secret")

    assert page.total == 0


def test_member_asking_for_potential_gigs_gets_none(service: GigService, make: Factory) -> None:
    make.complete_gig(status=GigStatus.POTENTIAL)

    page = list_for(service, make.member(), status=GigStatus.POTENTIAL)

    assert (page.total, page.items) == (0, [])


def test_manager_lists_every_gig_with_details(service: GigService, make: Factory) -> None:
    make.complete_gig(status=GigStatus.BOOKED)
    make.gig(venue_name="Draft")

    page = list_for(service, make.manager())

    assert page.total == 2
    assert all(row.restricted is False for row in page.items)


def test_manager_can_filter_by_status(service: GigService, make: Factory) -> None:
    make.complete_gig(status=GigStatus.BOOKED)
    draft = make.gig(venue_name="Draft")

    page = list_for(service, make.manager(), status=GigStatus.POTENTIAL)

    assert [row.id for row in page.items] == [draft.id]

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.models.enums import GigStatus, Role, SlotStatus
from app.models.gig import Gig
from app.repositories.gigs import GigRepository, MemberSlotFilter
from app.schemas.gigs import GigSort
from app.schemas.pagination import MAX_PAGE_SIZE
from tests.factories import BLUE_DOOR_FIRST_SET, Factory


def search(
    db: Session, *, page: int = 1, page_size: int = 25, **filters: Any
) -> tuple[list[Gig], int]:
    params: dict[str, Any] = {
        "q": None,
        "statuses": None,
        "has_date": None,
        "member_slot": None,
        "sort": GigSort.FIRST_SET_AT,
    }
    params.update(filters)
    return GigRepository(db).search(page=page, page_size=page_size, **params)


def make_dated_gigs(make: Factory, n: int) -> list[Gig]:
    return [
        make.gig(venue_name=f"Venue {i:03d}", first_set_at=BLUE_DOOR_FIRST_SET + timedelta(days=i))
        for i in range(n)
    ]


# ---- Filtering --------------------------------------------------------------------------------


def test_filters_by_status(db: Session, make: Factory) -> None:
    booked = make.gig(status=GigStatus.BOOKED)
    make.gig(status=GigStatus.POTENTIAL)

    gigs, total = search(db, statuses={GigStatus.BOOKED})

    assert ([g.id for g in gigs], total) == ([booked.id], 1)


def test_filters_dated_and_undated(db: Session, make: Factory) -> None:
    dated = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    undated = make.gig()

    assert [g.id for g in search(db, has_date=True)[0]] == [dated.id]
    assert [g.id for g in search(db, has_date=False)[0]] == [undated.id]
    assert search(db, has_date=None)[1] == 2


def test_filters_to_gigs_where_a_member_holds_a_slot_in_given_statuses(
    db: Session, make: Factory
) -> None:
    member = make.member()
    accepted = make.gig()
    make.slot(accepted, Role.BASS, member, SlotStatus.ACCEPTED)
    declined = make.gig()
    make.slot(declined, Role.BASS, member, SlotStatus.DECLINED)
    make.gig()

    gigs, total = search(
        db, member_slot=MemberSlotFilter(member.id, frozenset({SlotStatus.ACCEPTED}))
    )

    assert ([g.id for g in gigs], total) == ([accepted.id], 1)


def test_member_slot_filter_can_let_some_gig_statuses_through(db: Session, make: Factory) -> None:
    member = make.member()
    booked = make.gig(status=GigStatus.BOOKED)
    make.gig(status=GigStatus.POTENTIAL)

    gigs, _ = search(
        db,
        member_slot=MemberSlotFilter(
            member.id, frozenset({SlotStatus.INVITED}), frozenset({GigStatus.BOOKED})
        ),
    )

    assert [g.id for g in gigs] == [booked.id]


def test_finds_other_gigs_a_member_accepted(db: Session, make: Factory) -> None:
    member = make.member()
    this_gig, accepted, invited, cancelled = (
        make.gig(),
        make.gig(),
        make.gig(),
        make.gig(status=GigStatus.CANCELLED),
    )
    make.slot(this_gig, Role.BASS, member, SlotStatus.ACCEPTED)
    make.slot(accepted, Role.BASS, member, SlotStatus.ACCEPTED)
    make.slot(invited, Role.BASS, member, SlotStatus.INVITED)
    make.slot(cancelled, Role.BASS, member, SlotStatus.ACCEPTED)

    found = GigRepository(db).accepted_by_member(member.id, exclude_gig_id=this_gig.id)

    assert [g.id for g in found] == [accepted.id]


@pytest.mark.parametrize("q", ["blue door", "MAIN ST", "pat"])
def test_search_matches_venue_address_and_contact_names_case_insensitively(
    db: Session, make: Factory, q: str
) -> None:
    gig = make.gig(venue_name="The Blue Door", venue_address="123 Main St")
    make.contact(gig, name="Pat Lee")
    make.gig(venue_name="Hub City Tap")

    gigs, total = search(db, q=q)

    assert ([g.id for g in gigs], total) == ([gig.id], 1)


def test_search_treats_wildcard_characters_literally(db: Session, make: Factory) -> None:
    make.gig(venue_name="The Blue Door")

    assert search(db, q="%")[1] == 0
    assert search(db, q="_")[1] == 0


# ---- Sorting ----------------------------------------------------------------------------------


def test_sorts_by_first_set_with_undated_gigs_last(db: Session, make: Factory) -> None:
    undated = make.gig(venue_name="Undated")
    later = make.gig(first_set_at=BLUE_DOOR_FIRST_SET + timedelta(days=10))
    sooner = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)

    gigs, _ = search(db, sort=GigSort.FIRST_SET_AT)

    assert [g.id for g in gigs] == [sooner.id, later.id, undated.id]


def test_sorts_by_first_set_descending(db: Session, make: Factory) -> None:
    sooner = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    later = make.gig(first_set_at=BLUE_DOOR_FIRST_SET + timedelta(days=10))

    gigs, _ = search(db, sort=GigSort.FIRST_SET_AT_DESC)

    assert [g.id for g in gigs] == [later.id, sooner.id]


def test_sorts_by_venue_name(db: Session, make: Factory) -> None:
    hub = make.gig(venue_name="Hub City Tap")
    blue = make.gig(venue_name="The Blue Door")

    assert [g.id for g in search(db, sort=GigSort.VENUE_NAME)[0]] == [hub.id, blue.id]
    assert [g.id for g in search(db, sort=GigSort.VENUE_NAME_DESC)[0]] == [blue.id, hub.id]


def test_sorts_by_creation_time(db: Session, make: Factory) -> None:
    first = make.gig()
    second = make.gig()

    assert [g.id for g in search(db, sort=GigSort.CREATED_AT)[0]] == [first.id, second.id]
    assert [g.id for g in search(db, sort=GigSort.CREATED_AT_DESC)[0]] == [second.id, first.id]


# ---- Pagination boundaries ------------------------------------------------------------------


def test_first_page(db: Session, make: Factory) -> None:
    gigs = make_dated_gigs(make, 5)

    page, total = search(db, page=1, page_size=2)

    assert ([g.id for g in page], total) == ([gigs[0].id, gigs[1].id], 5)


def test_last_page_is_partial(db: Session, make: Factory) -> None:
    gigs = make_dated_gigs(make, 5)

    page, total = search(db, page=3, page_size=2)

    assert ([g.id for g in page], total) == ([gigs[4].id], 5)


def test_page_past_the_end_is_empty_but_keeps_the_total(db: Session, make: Factory) -> None:
    make_dated_gigs(make, 5)

    page, total = search(db, page=4, page_size=2)

    assert (page, total) == ([], 5)


def test_page_size_of_one(db: Session, make: Factory) -> None:
    gigs = make_dated_gigs(make, 3)

    page, total = search(db, page=2, page_size=1)

    assert ([g.id for g in page], total) == ([gigs[1].id], 3)


def test_page_size_at_its_maximum(db: Session, make: Factory) -> None:
    make_dated_gigs(make, MAX_PAGE_SIZE + 1)

    page, total = search(db, page=1, page_size=MAX_PAGE_SIZE)

    assert (len(page), total) == (MAX_PAGE_SIZE, MAX_PAGE_SIZE + 1)


def test_filters_by_first_set_range(db: Session, make: Factory) -> None:
    gigs = make_dated_gigs(make, 4)
    make.gig(venue_name="Undated")

    found, total = search(
        db,
        first_set_after=BLUE_DOOR_FIRST_SET + timedelta(days=1),
        first_set_before=BLUE_DOOR_FIRST_SET + timedelta(days=3),
    )

    assert [g.id for g in found] == [gigs[1].id, gigs[2].id]
    assert total == 2

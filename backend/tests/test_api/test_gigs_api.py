"""Each gig endpoint: the success case (status and shape) plus every error status it returns."""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.models.enums import GigStatus, Role, SlotStatus
from tests.factories import BLUE_DOOR_FIRST_SET, Factory, headers_for

pytestmark = pytest.mark.anyio

GIG_DETAIL_KEYS = {
    "id",
    "status",
    "first_set_at",
    "load_in_at",
    "soundcheck_at",
    "end_at",
    "load_in_offset_minutes",
    "soundcheck_offset_minutes",
    "performance_minutes",
    "venue_name",
    "venue_address",
    "lineup_size",
    "pay_cents",
    "slots",
    "contacts",
    "my_slot_id",
    "missing_for_booking",
    "created_at",
}


def assert_error(response_json: dict[str, str], code: str) -> None:
    assert set(response_json) == {"code", "detail"}
    assert response_json["code"] == code
    assert response_json["detail"]


# ---- Who is acting ------------------------------------------------------------------------


async def test_requests_without_an_acting_member_are_refused(client: AsyncClient) -> None:
    response = await client.get("/api/v1/gigs")

    assert response.status_code == 403
    assert_error(response.json(), "acting_member_required")


async def test_requests_from_an_unknown_member_are_refused(client: AsyncClient) -> None:
    response = await client.get("/api/v1/gigs", headers={"X-Acting-Member-Id": "9999"})

    assert response.status_code == 403
    assert_error(response.json(), "unknown_acting_member")


async def test_a_non_numeric_acting_member_fails_validation(client: AsyncClient) -> None:
    response = await client.get("/api/v1/gigs", headers={"X-Acting-Member-Id": "abc"})

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")


# ---- GET /gigs ------------------------------------------------------------------------------


async def test_list_returns_the_page_envelope(client: AsyncClient, make: Factory) -> None:
    gig = make.bookable_gig()

    response = await client.get("/api/v1/gigs", headers=headers_for(make.manager()))

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": gig.id,
                "status": "potential",
                "first_set_at": "2026-10-19T00:00:00Z",
                "venue_name": "The Blue Door",
                "lineup_size": "solo",
                "restricted": False,
                "my_slot_status": None,
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 25,
    }


async def test_list_passes_filters_and_paging_through(client: AsyncClient, make: Factory) -> None:
    make.bookable_gig()
    undated = make.gig(venue_name="Wedding inquiry")

    response = await client.get(
        "/api/v1/gigs",
        params={"has_date": "false", "page": 1, "page_size": 1, "sort": "-created_at"},
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [undated.id]
    assert (body["total"], body["page_size"]) == (1, 1)


@pytest.mark.parametrize(
    "params",
    [{"page_size": 101}, {"page_size": 0}, {"page": 0}, {"sort": "pay_cents"}, {"status": "maybe"}],
)
async def test_list_rejects_invalid_query_parameters(
    client: AsyncClient, make: Factory, params: dict[str, object]
) -> None:
    response = await client.get("/api/v1/gigs", params=params, headers=headers_for(make.manager()))

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")


# ---- POST /gigs -----------------------------------------------------------------------------


async def test_create_returns_201_with_location_and_the_new_gig(
    client: AsyncClient, make: Factory
) -> None:
    response = await client.post(
        "/api/v1/gigs",
        json={
            "first_set_at": "2026-10-18T20:00:00-04:00",
            "performance_minutes": 150,
            "venue_name": "The Blue Door",
            "pay_cents": 40000,
            "roles": ["rhythm_guitar_vocals", "lead_guitar"],
            "contacts": [
                {"label": "venue", "name": "Pat Lee", "phone": "555-0142"},
                {"label": "other", "notes": "Parking behind the building"},
            ],
        },
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == GIG_DETAIL_KEYS
    assert response.headers["location"] == f"/api/v1/gigs/{body['id']}"
    assert body["status"] == "potential"
    assert body["first_set_at"] == "2026-10-19T00:00:00Z"
    assert body["load_in_at"] == "2026-10-18T22:00:00Z"
    assert body["soundcheck_at"] == "2026-10-18T23:00:00Z"
    assert body["end_at"] == "2026-10-19T02:30:00Z"
    assert body["lineup_size"] == "duo"
    assert [(s["role"], s["status"], s["member"]) for s in body["slots"]] == [
        ("rhythm_guitar_vocals", "open", None),
        ("lead_guitar", "open", None),
    ]
    assert [{k: c[k] for k in ("label", "name", "phone", "notes")} for c in body["contacts"]] == [
        {"label": "venue", "name": "Pat Lee", "phone": "555-0142", "notes": None},
        {"label": "other", "name": None, "phone": None, "notes": "Parking behind the building"},
    ]
    assert "venue address" in body["missing_for_booking"]


async def test_the_band_leader_can_create_a_gig(client: AsyncClient, make: Factory) -> None:
    response = await client.post(
        "/api/v1/gigs", json={"venue_name": "Hub City Tap"}, headers=headers_for(make.leader())
    )

    assert response.status_code == 201
    assert response.json()["venue_name"] == "Hub City Tap"


async def test_create_by_a_member_is_refused(client: AsyncClient, make: Factory) -> None:
    response = await client.post(
        "/api/v1/gigs", json={"venue_name": "X"}, headers=headers_for(make.member())
    )

    assert response.status_code == 403
    assert_error(response.json(), "manager_or_band_leader_only")


@pytest.mark.parametrize(
    "body",
    [
        {"first_set_at": "2026-10-18T20:00:00"},  # no time zone
        {"pay_cents": -1},
        {"load_in_offset_minutes": 721},
        {"performance_minutes": 10},
        {"venue_name": "   "},
        {"roles": ["bass", "bass"]},
        {"roles": ["keytar"]},
        {"contacts": [{"label": "venue"}]},  # a contact with nothing in it
        {"contacts": [{"email": "not-an-email"}]},
        {"status": "booked"},  # status only changes through /book
    ],
)
async def test_create_rejects_invalid_bodies(
    client: AsyncClient, make: Factory, body: dict[str, object]
) -> None:
    response = await client.post("/api/v1/gigs", json=body, headers=headers_for(make.manager()))

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")


# ---- GET /gigs/{id} ---------------------------------------------------------------------------


async def test_get_returns_the_gig_detail(client: AsyncClient, make: Factory) -> None:
    gig = make.bookable_gig()

    response = await client.get(f"/api/v1/gigs/{gig.id}", headers=headers_for(make.manager()))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == GIG_DETAIL_KEYS
    assert (body["id"], body["pay_cents"], body["missing_for_booking"]) == (gig.id, 40000, [])
    assert body["slots"][0]["member"]["name"] == "Sam Rivera"


async def test_a_member_on_the_gig_gets_no_venue_contacts(
    client: AsyncClient, make: Factory
) -> None:
    gig = make.bookable_gig(status=GigStatus.BOOKED)
    riley = make.member()
    make.slot(gig, Role.BASS, riley, SlotStatus.ACCEPTED)

    response = await client.get(f"/api/v1/gigs/{gig.id}", headers=headers_for(riley))

    assert response.status_code == 200
    assert response.json()["contacts"] == []


async def test_get_a_missing_gig_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.get("/api/v1/gigs/9999", headers=headers_for(make.manager()))

    assert response.status_code == 404
    assert_error(response.json(), "gig_not_found")


async def test_get_a_gig_the_member_is_not_on_is_403(client: AsyncClient, make: Factory) -> None:
    gig = make.bookable_gig(status=GigStatus.BOOKED)

    response = await client.get(f"/api/v1/gigs/{gig.id}", headers=headers_for(make.member()))

    assert response.status_code == 403
    assert_error(response.json(), "not_assigned_to_gig")


# ---- PATCH /gigs/{id} ---------------------------------------------------------------------


async def test_patch_updates_fields_roles_and_contacts(client: AsyncClient, make: Factory) -> None:
    gig = make.bookable_gig()

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}",
        json={
            "pay_cents": 50000,
            "roles": ["rhythm_guitar_vocals", "drums"],
            "contacts": [{"label": "booking", "name": "Morgan Hale", "email": "m@example.com"}],
        },
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pay_cents"] == 50000
    assert [(s["role"], s["status"]) for s in body["slots"]] == [
        ("rhythm_guitar_vocals", "accepted"),
        ("drums", "open"),
    ]
    assert [c["name"] for c in body["contacts"]] == ["Morgan Hale"]


async def test_patch_a_missing_gig_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.patch(
        "/api/v1/gigs/9999", json={"pay_cents": 1}, headers=headers_for(make.manager())
    )

    assert response.status_code == 404
    assert_error(response.json(), "gig_not_found")


async def test_patch_by_a_member_is_403(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}", json={"pay_cents": 1}, headers=headers_for(make.member())
    )

    assert response.status_code == 403
    assert_error(response.json(), "manager_or_band_leader_only")


async def test_patch_that_leaves_a_booked_gig_incomplete_is_409(
    client: AsyncClient, make: Factory
) -> None:
    gig = make.bookable_gig(status=GigStatus.BOOKED)

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}", json={"contacts": []}, headers=headers_for(make.manager())
    )

    assert response.status_code == 409
    assert_error(response.json(), "gig_incomplete")


async def test_patch_with_an_invalid_body_is_422(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}", json={"pay_cents": "lots"}, headers=headers_for(make.manager())
    )

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")


# ---- POST /gigs/{id}/book -------------------------------------------------------------------


async def test_book_marks_the_gig_booked(client: AsyncClient, make: Factory) -> None:
    gig = make.bookable_gig()

    response = await client.post(f"/api/v1/gigs/{gig.id}/book", headers=headers_for(make.manager()))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == GIG_DETAIL_KEYS
    assert body["status"] == "booked"


async def test_book_an_incomplete_gig_is_409(client: AsyncClient, make: Factory) -> None:
    gig = make.gig(venue_name="The Blue Door")

    response = await client.post(f"/api/v1/gigs/{gig.id}/book", headers=headers_for(make.manager()))

    assert response.status_code == 409
    assert_error(response.json(), "gig_incomplete")
    assert "venue address" in response.json()["detail"]


async def test_book_by_a_member_is_403(client: AsyncClient, make: Factory) -> None:
    gig = make.bookable_gig()

    response = await client.post(f"/api/v1/gigs/{gig.id}/book", headers=headers_for(make.member()))

    assert response.status_code == 403
    assert_error(response.json(), "manager_or_band_leader_only")


async def test_book_a_missing_gig_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.post("/api/v1/gigs/9999/book", headers=headers_for(make.manager()))

    assert response.status_code == 404
    assert_error(response.json(), "gig_not_found")


async def test_book_with_a_non_numeric_id_is_422(client: AsyncClient, make: Factory) -> None:
    response = await client.post("/api/v1/gigs/abc/book", headers=headers_for(make.manager()))

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")


# ---- POST /gigs/{id}/slots/{slot_id}/invite -----------------------------------------------


async def test_invite_sets_the_member_and_their_pay(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS)
    riley = make.member(name="Riley Chen")

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}/invite",
        json={"member_id": riley.id, "pay_cents": 15000},
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == GIG_DETAIL_KEYS
    assert body["slots"] == [
        {
            "id": slot.id,
            "role": "bass",
            "status": "invited",
            "member": {"id": riley.id, "name": "Riley Chen"},
            "pay_cents": 15000,
            "responded_at": None,
        }
    ]


async def test_invite_by_a_member_is_403(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS)
    member = make.member()

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}/invite",
        json={"member_id": member.id},
        headers=headers_for(member),
    )

    assert response.status_code == 403
    assert_error(response.json(), "manager_or_band_leader_only")


async def test_invite_to_a_missing_slot_is_404(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/9999/invite",
        json={"member_id": 1},
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 404
    assert_error(response.json(), "slot_not_found")


async def test_invite_the_manager_is_409(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS)
    manager = make.manager()

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}/invite",
        json={"member_id": manager.id},
        headers=headers_for(manager),
    )

    assert response.status_code == 409
    assert_error(response.json(), "manager_cannot_play")


async def test_invite_without_a_member_is_422(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS)

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}/invite",
        json={"pay_cents": 100},
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")


# ---- PATCH /gigs/{id}/slots/{slot_id} -----------------------------------------------------


async def test_set_slot_pay(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, make.member(), pay_cents=10000)

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}",
        json={"pay_cents": 12500},
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 200
    assert response.json()["slots"][0]["pay_cents"] == 12500


async def test_the_band_leader_can_set_slot_pay(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, make.member(), pay_cents=10000)

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}",
        json={"pay_cents": 12500},
        headers=headers_for(make.leader()),
    )

    assert response.status_code == 200
    assert response.json()["slots"][0]["pay_cents"] == 12500


async def test_set_slot_pay_by_a_member_is_403(client: AsyncClient, make: Factory) -> None:
    member = make.member()
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, member)

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}",
        json={"pay_cents": 99999},
        headers=headers_for(member),
    )

    assert response.status_code == 403
    assert_error(response.json(), "manager_or_band_leader_only")


async def test_set_pay_on_a_missing_gig_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.patch(
        "/api/v1/gigs/9999/slots/1", json={"pay_cents": 1}, headers=headers_for(make.manager())
    )

    assert response.status_code == 404
    assert_error(response.json(), "gig_not_found")


async def test_set_negative_pay_is_422(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS)

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}",
        json={"pay_cents": -5},
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")


# ---- POST /gigs/{id}/slots/{slot_id}/accept and /decline ------------------------------------


async def test_accept_your_invitation(client: AsyncClient, make: Factory) -> None:
    riley = make.member()
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    slot = make.slot(gig, Role.BASS, riley, pay_cents=15000)

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}/accept", headers=headers_for(riley)
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == GIG_DETAIL_KEYS
    assert body["slots"][0]["status"] == "accepted"
    assert body["slots"][0]["responded_at"] is not None
    assert (body["my_slot_id"], body["pay_cents"], body["slots"][0]["pay_cents"]) == (
        slot.id,
        None,
        15000,
    )


async def test_decline_your_invitation(client: AsyncClient, make: Factory) -> None:
    riley = make.member()
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, riley)

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}/decline", headers=headers_for(riley)
    )

    assert response.status_code == 200
    assert response.json()["slots"][0]["status"] == "declined"


async def test_accept_someone_elses_invitation_is_403(client: AsyncClient, make: Factory) -> None:
    riley, taylor = make.member(), make.member(role=Role.DRUMS)
    gig = make.gig()
    make.slot(gig, Role.DRUMS, taylor)
    riley_slot = make.slot(gig, Role.BASS, riley)

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/{riley_slot.id}/accept", headers=headers_for(taylor)
    )

    assert response.status_code == 403
    assert_error(response.json(), "not_your_invitation")


async def test_accept_on_a_gig_you_are_not_invited_to_is_404(
    client: AsyncClient, make: Factory
) -> None:
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, make.member())

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}/accept", headers=headers_for(make.member())
    )

    assert response.status_code == 404
    assert_error(response.json(), "gig_not_found")


async def test_accept_an_overlapping_gig_is_409(client: AsyncClient, make: Factory) -> None:
    riley = make.member()
    other = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    make.slot(other, Role.BASS, riley, SlotStatus.ACCEPTED)
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET + timedelta(hours=1))
    slot = make.slot(gig, Role.BASS, riley)

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}/accept", headers=headers_for(riley)
    )

    assert response.status_code == 409
    assert_error(response.json(), "overlapping_gig")


async def test_decline_twice_is_409(client: AsyncClient, make: Factory) -> None:
    riley = make.member()
    gig = make.gig()
    slot = make.slot(gig, Role.BASS, riley, SlotStatus.DECLINED)

    response = await client.post(
        f"/api/v1/gigs/{gig.id}/slots/{slot.id}/decline", headers=headers_for(riley)
    )

    assert response.status_code == 409
    assert_error(response.json(), "invitation_not_pending")


async def test_answer_with_a_non_numeric_slot_is_422(client: AsyncClient, make: Factory) -> None:
    response = await client.post(
        "/api/v1/gigs/1/slots/abc/accept", headers=headers_for(make.member())
    )

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")


# ---- GET /gigs/{id}/availability ------------------------------------------------------------


async def test_get_gig_availability(client: AsyncClient, make: Factory) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)
    riley = make.member(name="Riley Chen", role=Role.BASS)
    make.busy_time(riley, BLUE_DOOR_FIRST_SET, BLUE_DOOR_FIRST_SET + timedelta(hours=1))

    response = await client.get(
        f"/api/v1/gigs/{gig.id}/availability", headers=headers_for(make.manager())
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"window_starts_at", "window_ends_at", "players"}
    assert body["window_starts_at"] == "2026-10-18T23:00:00Z"
    (player,) = body["players"]
    assert set(player) == {"member", "primary_role", "secondary_role", "busy", "conflicts"}
    assert (player["member"]["name"], player["busy"]) == ("Riley Chen", True)
    assert player["conflicts"][0]["kind"] == "busy_time"


async def test_gig_availability_for_a_member_is_403(client: AsyncClient, make: Factory) -> None:
    gig = make.gig(first_set_at=BLUE_DOOR_FIRST_SET)

    response = await client.get(
        f"/api/v1/gigs/{gig.id}/availability", headers=headers_for(make.member())
    )

    assert response.status_code == 403
    assert_error(response.json(), "manager_or_band_leader_only")


async def test_gig_availability_for_a_missing_gig_is_404(
    client: AsyncClient, make: Factory
) -> None:
    response = await client.get(
        "/api/v1/gigs/9999/availability", headers=headers_for(make.manager())
    )

    assert response.status_code == 404
    assert_error(response.json(), "gig_not_found")


async def test_gig_availability_with_a_non_numeric_id_is_422(
    client: AsyncClient, make: Factory
) -> None:
    response = await client.get(
        "/api/v1/gigs/abc/availability", headers=headers_for(make.manager())
    )

    assert response.status_code == 422

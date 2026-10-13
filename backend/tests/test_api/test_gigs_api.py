"""Each gig endpoint: the success case (status and shape) plus every error status it returns."""

import pytest
from httpx import AsyncClient

from app.models.enums import GigStatus, GigType, Role
from tests.factories import Factory, headers_for

pytestmark = pytest.mark.anyio

GIG_DETAIL_KEYS = {
    "id",
    "status",
    "first_set_at",
    "load_in_at",
    "soundcheck_at",
    "load_in_offset_minutes",
    "soundcheck_offset_minutes",
    "venue_name",
    "venue_address",
    "gig_type",
    "pay_cents",
    "venue_contact",
    "booking_contact",
    "lineup",
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
    gig = make.complete_gig()

    response = await client.get("/api/v1/gigs", headers=headers_for(make.manager()))

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": gig.id,
                "status": "potential",
                "first_set_at": "2026-10-19T00:00:00Z",
                "venue_name": "The Blue Door",
                "gig_type": "duo",
                "restricted": False,
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 25,
    }


async def test_list_passes_filters_and_paging_through(client: AsyncClient, make: Factory) -> None:
    make.complete_gig()
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
            "venue_name": "The Blue Door",
            "gig_type": "duo",
            "pay_cents": 40000,
            "venue_contact": {"name": "Pat Lee", "phone": "555-0142"},
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
    assert body["venue_contact"] == {"name": "Pat Lee", "phone": "555-0142", "email": None}
    assert body["booking_contact"] is None
    assert body["missing_for_booking"] == ["venue address"]
    assert body["lineup"] == [
        {"slot": "rhythm_guitar_vocals", "member": None},
        {"slot": "lead_guitar", "member": None},
    ]


async def test_create_by_a_member_is_refused(client: AsyncClient, make: Factory) -> None:
    response = await client.post(
        "/api/v1/gigs", json={"venue_name": "X"}, headers=headers_for(make.member())
    )

    assert response.status_code == 403
    assert_error(response.json(), "manager_only")


@pytest.mark.parametrize(
    "body",
    [
        {"first_set_at": "2026-10-18T20:00:00"},  # no time zone
        {"pay_cents": -1},
        {"load_in_offset_minutes": 721},
        {"venue_name": "   "},
        {"venue_contact": {"email": "not-an-email"}},
        {"gig_type": "quartet"},
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
    gig = make.complete_gig()

    response = await client.get(f"/api/v1/gigs/{gig.id}", headers=headers_for(make.manager()))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == GIG_DETAIL_KEYS
    assert (body["id"], body["pay_cents"], body["missing_for_booking"]) == (gig.id, 40000, [])


async def test_get_a_missing_gig_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.get("/api/v1/gigs/9999", headers=headers_for(make.manager()))

    assert response.status_code == 404
    assert_error(response.json(), "gig_not_found")


async def test_get_a_gig_the_member_is_not_on_is_403(client: AsyncClient, make: Factory) -> None:
    gig = make.complete_gig(status=GigStatus.BOOKED)

    response = await client.get(f"/api/v1/gigs/{gig.id}", headers=headers_for(make.member()))

    assert response.status_code == 403
    assert_error(response.json(), "not_assigned_to_gig")


# ---- PATCH /gigs/{id} ---------------------------------------------------------------------


async def test_patch_updates_and_assigns_the_lineup(client: AsyncClient, make: Factory) -> None:
    gig = make.complete_gig(gig_type=GigType.DUO)
    casey = make.member(name="Casey Morgan", role=Role.LEAD_GUITAR)

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}",
        json={"pay_cents": 50000, "lineup": [{"slot": "lead_guitar", "member_id": casey.id}]},
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pay_cents"] == 50000
    assert body["lineup"] == [
        {"slot": "rhythm_guitar_vocals", "member": None},
        {"slot": "lead_guitar", "member": {"id": casey.id, "name": "Casey Morgan"}},
    ]


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
    assert_error(response.json(), "manager_only")


async def test_patch_breaking_a_lineup_rule_is_409(client: AsyncClient, make: Factory) -> None:
    gig = make.complete_gig(gig_type=GigType.DUO)
    bassist = make.member(role=Role.BASS)

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}",
        json={"lineup": [{"slot": "lead_guitar", "member_id": bassist.id}]},
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 409
    assert_error(response.json(), "member_role_mismatch")


async def test_patch_with_an_invalid_body_is_422(client: AsyncClient, make: Factory) -> None:
    gig = make.gig()

    response = await client.patch(
        f"/api/v1/gigs/{gig.id}", json={"pay_cents": "lots"}, headers=headers_for(make.manager())
    )

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")


# ---- POST /gigs/{id}/book -------------------------------------------------------------------


async def test_book_marks_the_gig_booked(client: AsyncClient, make: Factory) -> None:
    gig = make.complete_gig()

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


async def test_book_twice_is_409(client: AsyncClient, make: Factory) -> None:
    gig = make.complete_gig(status=GigStatus.BOOKED)

    response = await client.post(f"/api/v1/gigs/{gig.id}/book", headers=headers_for(make.manager()))

    assert response.status_code == 409
    assert_error(response.json(), "gig_not_potential")


async def test_book_by_a_member_is_403(client: AsyncClient, make: Factory) -> None:
    gig = make.complete_gig()

    response = await client.post(f"/api/v1/gigs/{gig.id}/book", headers=headers_for(make.member()))

    assert response.status_code == 403
    assert_error(response.json(), "manager_only")


async def test_book_a_missing_gig_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.post("/api/v1/gigs/9999/book", headers=headers_for(make.manager()))

    assert response.status_code == 404
    assert_error(response.json(), "gig_not_found")


async def test_book_with_a_non_numeric_id_is_422(client: AsyncClient, make: Factory) -> None:
    response = await client.post("/api/v1/gigs/abc/book", headers=headers_for(make.manager()))

    assert response.status_code == 422
    assert_error(response.json(), "validation_error")

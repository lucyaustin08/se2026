from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.enums import InvitationStatus
from tests.factories import Factory, headers_for

pytestmark = pytest.mark.anyio

# 6:00 PM Eastern on Thu, Oct 22, 2026, with no gig that day.
START = datetime(2026, 10, 22, 22, 0, tzinfo=UTC)
PRACTICE_KEYS = {
    "id",
    "starts_at",
    "ends_at",
    "length_minutes",
    "location",
    "notes",
    "scheduled_by",
    "invitations",
    "my_status",
    "created_at",
}


# ---- GET /practices ------------------------------------------------------------------------


async def test_list_practices(client: AsyncClient, make: Factory) -> None:
    riley = make.member(name="Riley Chen")
    make.practice(START, [riley], location="Sam's garage")

    response = await client.get("/api/v1/practices", headers=headers_for(riley))

    assert response.status_code == 200
    page = response.json()
    assert (page["total"], page["page"], page["page_size"]) == (1, 1, 25)
    (item,) = page["items"]
    assert set(item) == PRACTICE_KEYS
    assert (item["location"], item["my_status"], item["ends_at"]) == (
        "Sam's garage",
        "invited",
        "2026-10-23T01:00:00Z",
    )


async def test_list_searches_location_and_notes(client: AsyncClient, make: Factory) -> None:
    riley = make.member()
    make.practice(START, [riley], location="Sam's garage")
    make.practice(START + timedelta(days=1), [riley], notes="Work on the new setlist")

    response = await client.get(
        "/api/v1/practices", params={"q": "setlist"}, headers=headers_for(riley)
    )

    assert [p["notes"] for p in response.json()["items"]] == ["Work on the new setlist"]


@pytest.mark.parametrize(
    "params", [{"page_size": 101}, {"sort": "location"}, {"starts_after": "2026-10-22T00:00:00"}]
)
async def test_list_with_invalid_parameters_is_422(
    client: AsyncClient, make: Factory, params: dict[str, object]
) -> None:
    response = await client.get(
        "/api/v1/practices", params=params, headers=headers_for(make.member())
    )

    assert response.status_code == 422


async def test_list_without_an_acting_member_is_403(client: AsyncClient) -> None:
    response = await client.get("/api/v1/practices")

    assert response.status_code == 403


# ---- POST /practices -----------------------------------------------------------------------


async def test_schedule_a_practice(client: AsyncClient, make: Factory) -> None:
    riley = make.member(name="Riley Chen")

    response = await client.post(
        "/api/v1/practices",
        json={"starts_at": START.isoformat(), "member_ids": [riley.id]},
        headers=headers_for(make.leader()),
    )

    assert response.status_code == 201
    created = response.json()
    assert set(created) == PRACTICE_KEYS
    assert created["length_minutes"] == 180
    assert created["invitations"][0]["member"]["name"] == "Riley Chen"
    assert response.headers["Location"] == f"/api/v1/practices/{created['id']}"


async def test_schedule_as_a_member_is_403(client: AsyncClient, make: Factory) -> None:
    riley = make.member()

    response = await client.post(
        "/api/v1/practices",
        json={"starts_at": START.isoformat(), "member_ids": [riley.id]},
        headers=headers_for(riley),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "manager_or_band_leader_only"


async def test_schedule_over_a_gig_is_409(client: AsyncClient, make: Factory) -> None:
    make.gig(first_set_at=START + timedelta(hours=2))

    response = await client.post(
        "/api/v1/practices",
        json={"starts_at": START.isoformat(), "member_ids": [make.member().id]},
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "practice_overlaps_gig"


async def test_schedule_on_a_gig_day_is_409_until_confirmed(
    client: AsyncClient, make: Factory
) -> None:
    make.gig(first_set_at=START + timedelta(hours=2))  # 8:00 PM Thursday locally
    body = {
        "starts_at": (START - timedelta(hours=8)).isoformat(),
        "member_ids": [make.member().id],
    }
    manager = make.manager()

    refused = await client.post("/api/v1/practices", json=body, headers=headers_for(manager))
    confirmed = await client.post(
        "/api/v1/practices",
        json={**body, "confirm_same_day": True},
        headers=headers_for(manager),
    )

    assert refused.status_code == 409
    assert refused.json()["code"] == "practice_same_day_as_gig"
    assert confirmed.status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        {"starts_at": "2026-10-22T22:00:00Z", "member_ids": []},
        {"starts_at": "2026-10-22T22:00:00Z", "member_ids": [1], "length_minutes": 10},
        {"starts_at": "2026-10-22T22:00:00", "member_ids": [1]},
        {"starts_at": "2026-10-22T22:00:00Z", "member_ids": [1], "status": "booked"},
    ],
    ids=["nobody invited", "too short", "no time zone", "extra field"],
)
async def test_schedule_invalid_practice_is_422(
    client: AsyncClient, make: Factory, body: dict[str, object]
) -> None:
    response = await client.post(
        "/api/v1/practices", json=body, headers=headers_for(make.manager())
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# ---- GET /practices/{id} -------------------------------------------------------------------


async def test_get_a_practice(client: AsyncClient, make: Factory) -> None:
    practice = make.practice(START, [make.member()])

    response = await client.get(
        f"/api/v1/practices/{practice.id}", headers=headers_for(make.manager())
    )

    assert response.status_code == 200
    assert set(response.json()) == PRACTICE_KEYS


async def test_get_a_practice_youre_not_invited_to_is_404(
    client: AsyncClient, make: Factory
) -> None:
    practice = make.practice(START, [make.member()])

    response = await client.get(
        f"/api/v1/practices/{practice.id}", headers=headers_for(make.member())
    )

    assert response.status_code == 404
    assert response.json()["code"] == "practice_not_found"


async def test_get_with_a_non_numeric_id_is_422(client: AsyncClient, make: Factory) -> None:
    response = await client.get("/api/v1/practices/abc", headers=headers_for(make.manager()))

    assert response.status_code == 422


# ---- POST /practices/{id}/accept and /decline ----------------------------------------------


@pytest.mark.parametrize(("answer", "status"), [("accept", "accepted"), ("decline", "declined")])
async def test_answer_a_practice(
    client: AsyncClient, make: Factory, answer: str, status: str
) -> None:
    riley = make.member()
    practice = make.practice(START, [riley])

    response = await client.post(
        f"/api/v1/practices/{practice.id}/{answer}", headers=headers_for(riley)
    )

    assert response.status_code == 200
    assert response.json()["my_status"] == status


async def test_answer_twice_is_409(client: AsyncClient, make: Factory) -> None:
    riley = make.member()
    practice = make.practice(START, [riley], status=InvitationStatus.DECLINED)

    response = await client.post(
        f"/api/v1/practices/{practice.id}/accept", headers=headers_for(riley)
    )

    assert response.status_code == 409
    assert response.json()["code"] == "invitation_not_pending"


async def test_answer_a_practice_youre_not_invited_to_is_404(
    client: AsyncClient, make: Factory
) -> None:
    practice = make.practice(START, [make.member()])

    response = await client.post(
        f"/api/v1/practices/{practice.id}/accept", headers=headers_for(make.member())
    )

    assert response.status_code == 404


async def test_answer_without_an_acting_member_is_403(client: AsyncClient, make: Factory) -> None:
    practice = make.practice(START, [make.member()])

    response = await client.post(f"/api/v1/practices/{practice.id}/accept")

    assert response.status_code == 403


async def test_answer_with_a_non_numeric_id_is_422(client: AsyncClient, make: Factory) -> None:
    response = await client.post(
        "/api/v1/practices/abc/decline", headers=headers_for(make.member())
    )

    assert response.status_code == 422

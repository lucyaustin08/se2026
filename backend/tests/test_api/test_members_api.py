import pytest
from httpx import AsyncClient

from app.models.enums import Role
from tests.factories import Factory, headers_for

pytestmark = pytest.mark.anyio


async def test_lists_members_without_an_acting_member(client: AsyncClient, make: Factory) -> None:
    manager = make.manager(name="Jordan Avery")
    bassist = make.member(name="Riley Chen", role=Role.BASS)

    response = await client.get("/api/v1/members")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": manager.id,
                "name": "Jordan Avery",
                "primary_role": None,
                "is_manager": True,
                "is_band_leader": False,
            },
            {
                "id": bassist.id,
                "name": "Riley Chen",
                "primary_role": "bass",
                "is_manager": False,
                "is_band_leader": False,
            },
        ],
        "total": 2,
        "page": 1,
        "page_size": 25,
    }


async def test_searches_and_pages(client: AsyncClient, make: Factory) -> None:
    make.member(name="Riley Chen")
    make.member(name="Casey Morgan")

    response = await client.get("/api/v1/members", params={"q": "casey", "page_size": 1})

    body = response.json()
    assert [m["name"] for m in body["items"]] == ["Casey Morgan"]
    assert (body["total"], body["page_size"]) == (1, 1)


@pytest.mark.parametrize("params", [{"page_size": 101}, {"page": 0}, {"sort": "email"}])
async def test_rejects_invalid_query_parameters(
    client: AsyncClient, params: dict[str, object]
) -> None:
    response = await client.get("/api/v1/members", params=params)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# ---- GET /members/{id} -------------------------------------------------------------------

PROFILE_KEYS = {
    "id",
    "name",
    "email",
    "phone",
    "primary_role",
    "secondary_role",
    "is_manager",
    "is_band_leader",
}


async def test_get_your_own_profile(client: AsyncClient, make: Factory) -> None:
    riley = make.member(name="Riley Chen", phone="555-0103")

    response = await client.get(f"/api/v1/members/{riley.id}", headers=headers_for(riley))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PROFILE_KEYS
    assert (body["name"], body["email"], body["phone"]) == ("Riley Chen", riley.email, "555-0103")


async def test_another_member_gets_no_contact_details(client: AsyncClient, make: Factory) -> None:
    riley = make.member(phone="555-0103")

    response = await client.get(f"/api/v1/members/{riley.id}", headers=headers_for(make.member()))

    assert response.status_code == 200
    assert (response.json()["email"], response.json()["phone"]) == (None, None)


async def test_get_a_profile_without_an_acting_member_is_403(
    client: AsyncClient, make: Factory
) -> None:
    response = await client.get(f"/api/v1/members/{make.member().id}")

    assert response.status_code == 403
    assert response.json()["code"] == "acting_member_required"


async def test_get_a_missing_member_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.get("/api/v1/members/9999", headers=headers_for(make.member()))

    assert response.status_code == 404
    assert response.json()["code"] == "member_not_found"


async def test_get_with_a_non_numeric_id_is_422(client: AsyncClient, make: Factory) -> None:
    response = await client.get("/api/v1/members/abc", headers=headers_for(make.member()))

    assert response.status_code == 422


# ---- PATCH /members/{id} -----------------------------------------------------------------


async def test_patch_your_own_profile(client: AsyncClient, make: Factory) -> None:
    riley = make.member(role=Role.BASS)

    response = await client.patch(
        f"/api/v1/members/{riley.id}",
        json={"phone": "555-0199", "secondary_role": "drums"},
        headers=headers_for(riley),
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PROFILE_KEYS
    assert (body["phone"], body["primary_role"], body["secondary_role"]) == (
        "555-0199",
        "bass",
        "drums",
    )


async def test_patch_someone_elses_profile_is_403(client: AsyncClient, make: Factory) -> None:
    riley = make.member()

    response = await client.patch(
        f"/api/v1/members/{riley.id}", json={"name": "X"}, headers=headers_for(make.manager())
    )

    assert response.status_code == 403
    assert response.json()["code"] == "not_your_profile"


async def test_patch_a_missing_member_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.patch(
        "/api/v1/members/9999", json={"name": "X"}, headers=headers_for(make.member())
    )

    assert response.status_code == 404
    assert response.json()["code"] == "member_not_found"


async def test_patch_with_a_taken_email_is_409(client: AsyncClient, make: Factory) -> None:
    casey = make.member()
    riley = make.member()

    response = await client.patch(
        f"/api/v1/members/{riley.id}", json={"email": casey.email}, headers=headers_for(riley)
    )

    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


async def test_patch_with_the_same_instrument_twice_is_409(
    client: AsyncClient, make: Factory
) -> None:
    riley = make.member(role=Role.BASS)

    response = await client.patch(
        f"/api/v1/members/{riley.id}", json={"secondary_role": "bass"}, headers=headers_for(riley)
    )

    assert response.status_code == 409
    assert response.json()["code"] == "secondary_same_as_primary"


@pytest.mark.parametrize(
    "body",
    [
        {"name": ""},
        {"name": None},
        {"email": "not-an-email"},
        {"email": None},
        {"is_band_leader": True},
        {"is_manager": True},
    ],
    ids=["blank name", "null name", "bad email", "null email", "leader flag", "manager flag"],
)
async def test_patch_with_invalid_fields_is_422(
    client: AsyncClient, make: Factory, body: dict[str, object]
) -> None:
    riley = make.member()

    response = await client.patch(
        f"/api/v1/members/{riley.id}", json=body, headers=headers_for(riley)
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"

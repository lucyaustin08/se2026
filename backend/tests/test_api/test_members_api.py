import pytest
from httpx import AsyncClient

from app.models.enums import Role
from tests.factories import Factory

pytestmark = pytest.mark.anyio


async def test_lists_members_without_an_acting_member(client: AsyncClient, make: Factory) -> None:
    manager = make.manager(name="Jordan Avery")
    bassist = make.member(name="Riley Chen", role=Role.BASS)

    response = await client.get("/api/v1/members")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": manager.id, "name": "Jordan Avery", "primary_role": None, "is_manager": True},
            {"id": bassist.id, "name": "Riley Chen", "primary_role": "bass", "is_manager": False},
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

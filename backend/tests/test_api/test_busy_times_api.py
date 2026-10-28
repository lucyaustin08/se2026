from datetime import timedelta

import pytest
from httpx import AsyncClient

from tests.factories import BLUE_DOOR_FIRST_SET, Factory, headers_for

pytestmark = pytest.mark.anyio

START = BLUE_DOOR_FIRST_SET
BUSY_TIME_KEYS = {"id", "member", "starts_at", "ends_at", "created_at"}


def body(hours_from: int = 0, hours_to: int = 2) -> dict[str, str]:
    return {
        "starts_at": (START + timedelta(hours=hours_from)).isoformat(),
        "ends_at": (START + timedelta(hours=hours_to)).isoformat(),
    }


# ---- GET /busy-times -----------------------------------------------------------------------


async def test_list_your_own_busy_times(client: AsyncClient, make: Factory) -> None:
    riley = make.member(name="Riley Chen")
    make.busy_time(riley, START, START + timedelta(hours=2))

    response = await client.get("/api/v1/busy-times", headers=headers_for(riley))

    assert response.status_code == 200
    page = response.json()
    assert (page["total"], page["page"], page["page_size"]) == (1, 1, 25)
    (item,) = page["items"]
    assert set(item) == BUSY_TIME_KEYS
    assert item["member"] == {"id": riley.id, "name": "Riley Chen"}
    assert item["starts_at"] == "2026-10-19T00:00:00Z"


async def test_list_someone_elses_busy_times_as_a_member_is_403(
    client: AsyncClient, make: Factory
) -> None:
    other = make.member()

    response = await client.get(
        "/api/v1/busy-times", params={"member_id": other.id}, headers=headers_for(make.member())
    )

    assert response.status_code == 403
    assert response.json()["code"] == "availability_private"


@pytest.mark.parametrize(
    "params",
    [
        {"page_size": 101},
        {"sort": "ends_at"},
        {"ends_after": "x"},
        {"ends_after": "2026-10-19T00:00:00"},
    ],
)
async def test_list_with_invalid_parameters_is_422(
    client: AsyncClient, make: Factory, params: dict[str, object]
) -> None:
    response = await client.get(
        "/api/v1/busy-times", params=params, headers=headers_for(make.member())
    )

    assert response.status_code == 422


# ---- POST /busy-times ----------------------------------------------------------------------


async def test_add_a_busy_time(client: AsyncClient, make: Factory) -> None:
    riley = make.member()

    response = await client.post("/api/v1/busy-times", json=body(), headers=headers_for(riley))

    assert response.status_code == 201
    created = response.json()
    assert set(created) == BUSY_TIME_KEYS
    assert created["member"]["id"] == riley.id
    assert response.headers["Location"] == f"/api/v1/busy-times/{created['id']}"


async def test_add_without_an_acting_member_is_403(client: AsyncClient) -> None:
    response = await client.post("/api/v1/busy-times", json=body())

    assert response.status_code == 403
    assert response.json()["code"] == "acting_member_required"


@pytest.mark.parametrize(
    "payload",
    [body(2, 2), body(3, 1), {"starts_at": "2026-10-19T00:00:00"}, {**body(), "note": "x"}],
    ids=["zero length", "ends first", "no time zone and no end", "extra field"],
)
async def test_add_an_invalid_busy_time_is_422(
    client: AsyncClient, make: Factory, payload: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/busy-times", json=payload, headers=headers_for(make.member())
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# ---- PATCH and DELETE /busy-times/{id} -----------------------------------------------------


async def test_change_your_busy_time(client: AsyncClient, make: Factory) -> None:
    riley = make.member()
    busy_time = make.busy_time(riley, START, START + timedelta(hours=2))

    response = await client.patch(
        f"/api/v1/busy-times/{busy_time.id}", json=body(1, 4), headers=headers_for(riley)
    )

    assert response.status_code == 200
    assert response.json()["ends_at"] == "2026-10-19T04:00:00Z"


async def test_change_someone_elses_busy_time_is_403(client: AsyncClient, make: Factory) -> None:
    busy_time = make.busy_time(make.member(), START, START + timedelta(hours=2))

    response = await client.patch(
        f"/api/v1/busy-times/{busy_time.id}", json=body(), headers=headers_for(make.leader())
    )

    assert response.status_code == 403
    assert response.json()["code"] == "not_your_busy_time"


async def test_change_a_missing_busy_time_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.patch(
        "/api/v1/busy-times/9999", json=body(), headers=headers_for(make.member())
    )

    assert response.status_code == 404
    assert response.json()["code"] == "busy_time_not_found"


async def test_change_with_an_end_before_the_start_is_422(
    client: AsyncClient, make: Factory
) -> None:
    riley = make.member()
    busy_time = make.busy_time(riley, START, START + timedelta(hours=2))

    response = await client.patch(
        f"/api/v1/busy-times/{busy_time.id}", json=body(3, 1), headers=headers_for(riley)
    )

    assert response.status_code == 422


async def test_delete_your_busy_time(client: AsyncClient, make: Factory) -> None:
    riley = make.member()
    busy_time = make.busy_time(riley, START, START + timedelta(hours=2))

    response = await client.delete(f"/api/v1/busy-times/{busy_time.id}", headers=headers_for(riley))
    listed = await client.get("/api/v1/busy-times", headers=headers_for(riley))

    assert (response.status_code, response.content) == (204, b"")
    assert listed.json()["total"] == 0


async def test_delete_someone_elses_busy_time_is_403(client: AsyncClient, make: Factory) -> None:
    busy_time = make.busy_time(make.member(), START, START + timedelta(hours=2))

    response = await client.delete(
        f"/api/v1/busy-times/{busy_time.id}", headers=headers_for(make.manager())
    )

    assert response.status_code == 403


async def test_delete_a_missing_busy_time_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.delete("/api/v1/busy-times/9999", headers=headers_for(make.member()))

    assert response.status_code == 404


async def test_delete_with_a_non_numeric_id_is_422(client: AsyncClient, make: Factory) -> None:
    response = await client.delete("/api/v1/busy-times/abc", headers=headers_for(make.member()))

    assert response.status_code == 422

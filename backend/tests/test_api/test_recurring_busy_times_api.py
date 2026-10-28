from datetime import UTC, date, datetime, time

import pytest
from httpx import AsyncClient

from tests.factories import Factory, headers_for

pytestmark = pytest.mark.anyio

RULE_KEYS = {
    "id",
    "member",
    "weekdays",
    "start_time",
    "end_time",
    "starts_on",
    "ends_on",
    "time_zone",
    "created_at",
}
PERIOD_KEYS = {"kind", "source_id", "member", "starts_at", "ends_at"}


def body(**fields: object) -> dict[str, object]:
    data: dict[str, object] = {
        "weekdays": [1, 2, 3, 4, 5],
        "start_time": "08:00:00",
        "end_time": "17:00:00",
        "starts_on": "2026-11-02",
    }
    data.update(fields)
    return data


# ---- GET /recurring-busy-times ---------------------------------------------------------------


async def test_list_your_own_weekly_busy_times(client: AsyncClient, make: Factory) -> None:
    riley = make.member(name="Riley Chen")
    make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))
    make.weekly(make.member(), [3], time(18), time(21), date(2026, 11, 1))

    response = await client.get("/api/v1/recurring-busy-times", headers=headers_for(riley))

    assert response.status_code == 200
    page = response.json()
    assert (page["total"], page["page"], page["page_size"]) == (1, 1, 25)
    (item,) = page["items"]
    assert set(item) == RULE_KEYS
    assert item["member"] == {"id": riley.id, "name": "Riley Chen"}
    assert (item["weekdays"], item["start_time"], item["end_time"]) == ([2], "18:00:00", "21:00:00")
    assert (item["starts_on"], item["ends_on"]) == ("2026-11-01", None)


async def test_list_someone_elses_weekly_busy_times_as_a_member_is_403(
    client: AsyncClient, make: Factory
) -> None:
    response = await client.get(
        "/api/v1/recurring-busy-times",
        params={"member_id": make.member().id},
        headers=headers_for(make.member()),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "availability_private"


@pytest.mark.parametrize("params", [{"page_size": 101}, {"page": 0}, {"sort": "start_time"}])
async def test_list_with_invalid_parameters_is_422(
    client: AsyncClient, make: Factory, params: dict[str, object]
) -> None:
    response = await client.get(
        "/api/v1/recurring-busy-times", params=params, headers=headers_for(make.member())
    )

    assert response.status_code == 422


# ---- POST /recurring-busy-times --------------------------------------------------------------


async def test_add_a_weekly_busy_time(client: AsyncClient, make: Factory) -> None:
    riley = make.member()

    response = await client.post(
        "/api/v1/recurring-busy-times", json=body(), headers=headers_for(riley)
    )

    assert response.status_code == 201
    created = response.json()
    assert set(created) == RULE_KEYS
    assert created["member"]["id"] == riley.id
    assert created["time_zone"] == "America/New_York"
    assert response.headers["Location"] == f"/api/v1/recurring-busy-times/{created['id']}"


async def test_add_without_an_acting_member_is_403(client: AsyncClient) -> None:
    response = await client.post("/api/v1/recurring-busy-times", json=body())

    assert response.status_code == 403
    assert response.json()["code"] == "acting_member_required"


@pytest.mark.parametrize(
    "payload",
    [
        body(end_time="08:00:00"),
        body(ends_on="2026-11-01"),
        body(weekdays=[]),
        body(weekdays=[0]),
        body(start_time="8 AM"),
        {"weekdays": [1]},
        body(reason="work"),
    ],
    ids=[
        "same start and end",
        "last date first",
        "no days",
        "day zero",
        "unreadable time",
        "missing fields",
        "extra field",
    ],
)
async def test_add_an_invalid_weekly_busy_time_is_422(
    client: AsyncClient, make: Factory, payload: dict[str, object]
) -> None:
    response = await client.post(
        "/api/v1/recurring-busy-times", json=payload, headers=headers_for(make.member())
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# ---- PATCH and DELETE /recurring-busy-times/{id} --------------------------------------------


async def test_change_your_weekly_busy_time(client: AsyncClient, make: Factory) -> None:
    riley = make.member()
    rule = make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))

    response = await client.patch(
        f"/api/v1/recurring-busy-times/{rule.id}",
        json=body(weekdays=[6], start_time="22:00:00", end_time="02:00:00"),
        headers=headers_for(riley),
    )

    assert response.status_code == 200
    changed = response.json()
    assert (changed["weekdays"], changed["start_time"], changed["end_time"]) == (
        [6],
        "22:00:00",
        "02:00:00",
    )


async def test_change_someone_elses_weekly_busy_time_is_403(
    client: AsyncClient, make: Factory
) -> None:
    rule = make.weekly(make.member(), [2], time(18), time(21), date(2026, 11, 1))

    response = await client.patch(
        f"/api/v1/recurring-busy-times/{rule.id}", json=body(), headers=headers_for(make.leader())
    )

    assert response.status_code == 403
    assert response.json()["code"] == "not_your_busy_time"


async def test_change_a_missing_weekly_busy_time_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.patch(
        "/api/v1/recurring-busy-times/9999", json=body(), headers=headers_for(make.member())
    )

    assert response.status_code == 404
    assert response.json()["code"] == "recurring_busy_time_not_found"


async def test_change_with_the_same_start_and_end_is_422(
    client: AsyncClient, make: Factory
) -> None:
    riley = make.member()
    rule = make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))

    response = await client.patch(
        f"/api/v1/recurring-busy-times/{rule.id}",
        json=body(end_time="08:00:00"),
        headers=headers_for(riley),
    )

    assert response.status_code == 422


async def test_delete_your_weekly_busy_time(client: AsyncClient, make: Factory) -> None:
    riley = make.member()
    rule = make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))

    response = await client.delete(
        f"/api/v1/recurring-busy-times/{rule.id}", headers=headers_for(riley)
    )
    listed = await client.get("/api/v1/recurring-busy-times", headers=headers_for(riley))

    assert (response.status_code, response.content) == (204, b"")
    assert listed.json()["total"] == 0


async def test_delete_someone_elses_weekly_busy_time_is_403(
    client: AsyncClient, make: Factory
) -> None:
    rule = make.weekly(make.member(), [2], time(18), time(21), date(2026, 11, 1))

    response = await client.delete(
        f"/api/v1/recurring-busy-times/{rule.id}", headers=headers_for(make.manager())
    )

    assert response.status_code == 403


async def test_delete_a_missing_weekly_busy_time_is_404(client: AsyncClient, make: Factory) -> None:
    response = await client.delete(
        "/api/v1/recurring-busy-times/9999", headers=headers_for(make.member())
    )

    assert response.status_code == 404


# ---- GET /busy-times/periods -----------------------------------------------------------------


async def test_busy_periods_for_a_week(client: AsyncClient, make: Factory) -> None:
    riley = make.member(name="Riley Chen")
    rule = make.weekly(riley, [2], time(18), time(21), date(2026, 11, 1))
    trip = make.busy_time(
        riley, datetime(2026, 11, 13, 14, tzinfo=UTC), datetime(2026, 11, 13, 20, tzinfo=UTC)
    )

    response = await client.get(
        "/api/v1/busy-times/periods",
        params={"ends_after": "2026-11-08T05:00:00Z", "starts_before": "2026-11-15T05:00:00Z"},
        headers=headers_for(make.manager()),
    )

    assert response.status_code == 200
    result = response.json()
    assert (result["ends_after"], result["starts_before"]) == (
        "2026-11-08T05:00:00Z",
        "2026-11-15T05:00:00Z",
    )
    assert all(set(period) == PERIOD_KEYS for period in result["periods"])
    assert [
        (p["kind"], p["source_id"], p["member"]["name"], p["starts_at"], p["ends_at"])
        for p in result["periods"]
    ] == [
        ("weekly", rule.id, "Riley Chen", "2026-11-10T23:00:00Z", "2026-11-11T02:00:00Z"),
        ("one_off", trip.id, "Riley Chen", "2026-11-13T14:00:00Z", "2026-11-13T20:00:00Z"),
    ]


async def test_a_member_gets_only_their_own_busy_periods(
    client: AsyncClient, make: Factory
) -> None:
    riley = make.member()
    make.weekly(make.member(), [2], time(18), time(21), date(2026, 11, 1))

    response = await client.get(
        "/api/v1/busy-times/periods",
        params={"ends_after": "2026-11-08T05:00:00Z", "starts_before": "2026-11-15T05:00:00Z"},
        headers=headers_for(riley),
    )

    assert response.status_code == 200
    assert response.json()["periods"] == []


@pytest.mark.parametrize(
    "params",
    [
        {"ends_after": "2026-11-01T00:00:00Z", "starts_before": "2027-01-03T00:00:00Z"},
        {"ends_after": "2026-11-08T00:00:00Z", "starts_before": "2026-11-01T00:00:00Z"},
        {"ends_after": "2026-11-01T00:00:00", "starts_before": "2026-11-08T00:00:00"},
        {"ends_after": "2026-11-01T00:00:00Z"},
    ],
    ids=["more than 62 days", "backwards", "no time zone", "missing end"],
)
async def test_busy_periods_with_an_unusable_range_is_422(
    client: AsyncClient, make: Factory, params: dict[str, str]
) -> None:
    response = await client.get(
        "/api/v1/busy-times/periods", params=params, headers=headers_for(make.member())
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"

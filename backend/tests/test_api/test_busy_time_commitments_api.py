from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.models.enums import InvitationStatus
from tests.factories import Factory, headers_for

pytestmark = pytest.mark.anyio

# Tue, Mar 2, 2027, 6:00 PM Eastern standard time.
PRACTICE_AT = datetime(2027, 3, 2, 23, 0, tzinfo=UTC)
OVERLAPPING = {"starts_at": "2027-03-02T22:00:00Z", "ends_at": "2027-03-03T00:00:00Z"}
WEEKLY = {"weekdays": [2], "start_time": "17:00", "end_time": "19:00", "starts_on": "2027-03-01"}


@pytest.mark.parametrize("path", ["/api/v1/busy-times", "/api/v1/recurring-busy-times"])
async def test_a_busy_time_over_an_accepted_practice_is_409(
    client: AsyncClient, make: Factory, path: str
) -> None:
    riley = make.member()
    make.practice(PRACTICE_AT, [riley], status=InvitationStatus.ACCEPTED)
    body = OVERLAPPING if path.endswith("/busy-times") else WEEKLY

    response = await client.post(path, json=body, headers=headers_for(riley))

    assert response.status_code == 409
    assert response.json()["code"] == "busy_time_overlaps_accepted"


@pytest.mark.parametrize("path", ["/api/v1/busy-times", "/api/v1/recurring-busy-times"])
async def test_a_busy_time_over_an_invitation_is_409_until_confirmed(
    client: AsyncClient, make: Factory, path: str
) -> None:
    riley = make.member()
    make.practice(PRACTICE_AT, [riley])
    body = OVERLAPPING if path.endswith("/busy-times") else WEEKLY

    warned = await client.post(path, json=body, headers=headers_for(riley))
    confirmed = await client.post(
        path, json={**body, "decline_invitations": True}, headers=headers_for(riley)
    )
    practices = await client.get("/api/v1/practices", headers=headers_for(riley))

    assert warned.status_code == 409
    assert warned.json()["code"] == "busy_time_overlaps_invitation"
    assert confirmed.status_code == 201
    (practice,) = practices.json()["items"]
    assert practice["my_status"] == "declined"

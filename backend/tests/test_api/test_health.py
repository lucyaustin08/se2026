import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_health_reports_ok_when_database_answers(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

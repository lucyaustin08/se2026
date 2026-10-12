"""Every error, whatever raised it, comes back as {"code": ..., "detail": ...}."""

from collections.abc import AsyncIterator
from typing import Annotated

import pytest
from fastapi import APIRouter, FastAPI, Query
from httpx import ASGITransport, AsyncClient

from app.core.errors import AppError, BusinessRuleViolation, NotFoundError, PermissionDeniedError

pytestmark = pytest.mark.anyio

DOMAIN_ERRORS: dict[str, AppError] = {
    "not-found": NotFoundError("That gig does not exist.", code="gig_not_found"),
    "forbidden": PermissionDeniedError("Only the manager can book gigs.", code="manager_only"),
    "conflict": BusinessRuleViolation("The gig is missing pay.", code="gig_incomplete"),
}


def _add_test_routes(app: FastAPI) -> None:
    router = APIRouter(prefix="/test-errors")

    @router.get("/domain/{name}")
    def raise_domain_error(name: str) -> None:
        raise DOMAIN_ERRORS[name]

    @router.get("/validated")
    def validated(page: Annotated[int, Query(ge=1)]) -> dict[str, int]:
        return {"page": page}

    @router.get("/crash")
    def crash() -> None:
        raise RuntimeError("unexpected failure")

    app.include_router(router)


@pytest.fixture
async def error_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    _add_test_routes(app)
    # Return the 500 response instead of re-raising, as a real server would.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.parametrize(
    ("name", "status", "code"),
    [
        ("not-found", 404, "gig_not_found"),
        ("forbidden", 403, "manager_only"),
        ("conflict", 409, "gig_incomplete"),
    ],
)
async def test_domain_errors_map_to_status_and_keep_their_code(
    error_client: AsyncClient, name: str, status: int, code: str
) -> None:
    response = await error_client.get(f"/test-errors/domain/{name}")

    assert response.status_code == status
    assert response.json() == {"code": code, "detail": DOMAIN_ERRORS[name].detail}


async def test_domain_error_without_custom_code_uses_its_default_code(app: FastAPI) -> None:
    router = APIRouter()

    @router.get("/default-code")
    def raise_default() -> None:
        raise BusinessRuleViolation("Refused.")

    app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get("/default-code")

    assert response.status_code == 409
    assert response.json() == {"code": "business_rule_violation", "detail": "Refused."}


async def test_unknown_route_returns_not_found_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert response.json()["detail"]


async def test_wrong_method_returns_405_envelope_and_keeps_allow_header(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"
    assert "GET" in response.headers["allow"]


async def test_schema_validation_failure_returns_422_naming_the_field(
    error_client: AsyncClient,
) -> None:
    response = await error_client.get("/test-errors/validated", params={"page": 0})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert "page" in body["detail"]
    assert set(body) == {"code", "detail"}


async def test_unexpected_exception_returns_500_without_leaking_internals(
    error_client: AsyncClient,
) -> None:
    response = await error_client.get("/test-errors/crash")

    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "detail": "Something went wrong on the server.",
    }

"""OpenAPI descriptions of error responses, so generated frontend types know their shape."""

from typing import Any

from app.schemas.errors import ErrorResponse


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    return {status_code: {"model": ErrorResponse} for status_code in status_codes}

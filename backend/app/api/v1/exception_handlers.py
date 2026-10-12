"""Turn every error into the standard envelope: {"code": ..., "detail": ...}."""

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, BusinessRuleViolation, NotFoundError, PermissionDeniedError
from app.schemas.errors import ErrorResponse

STATUS_BY_ERROR: dict[type[AppError], int] = {
    NotFoundError: 404,
    PermissionDeniedError: 403,
    BusinessRuleViolation: 409,
}

_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    404: ("not_found", "The requested resource was not found."),
    405: ("method_not_allowed", "This HTTP method is not allowed for this resource."),
}


def _envelope(
    status_code: int, code: str, detail: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    body = ErrorResponse(code=code, detail=detail).model_dump()
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def _status_for(error: AppError) -> int:
    for error_type in type(error).__mro__:
        if error_type in STATUS_BY_ERROR:
            return STATUS_BY_ERROR[error_type]
    return 500


async def handle_app_error(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):  # pragma: no cover - registered for AppError only
        raise exc
    return _envelope(_status_for(exc), exc.code, exc.detail)


async def handle_http_exception(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover
        raise exc
    default = (f"http_{exc.status_code}", f"{HTTPStatus(exc.status_code).phrase}.")
    code, detail = _HTTP_ERRORS.get(exc.status_code, default)
    return _envelope(exc.status_code, code, detail, headers=exc.headers)


async def handle_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # pragma: no cover
        raise exc
    problems = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = str(error.get("msg", "Invalid value"))
        problems.append(f"{location}: {message}" if location else message)
    detail = "The request is invalid. " + "; ".join(problems) + "."
    return _envelope(422, "validation_error", detail)


async def handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
    return _envelope(500, "internal_error", "Something went wrong on the server.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)

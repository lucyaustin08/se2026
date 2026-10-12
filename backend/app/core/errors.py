"""Domain error types.

Services and repositories raise these. They carry a machine-readable `code` and a
human-readable `detail`, and know nothing about HTTP: the mapping to status codes lives
in `app.api.v1.exception_handlers`.
"""


class AppError(Exception):
    """Base class for errors the API turns into the standard error envelope."""

    code: str = "app_error"

    def __init__(self, detail: str, *, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    """The requested resource does not exist."""

    code = "not_found"


class PermissionDeniedError(AppError):
    """The acting user is not allowed to do this."""

    code = "permission_denied"


class BusinessRuleViolation(AppError):
    """A business rule refused an otherwise valid request."""

    code = "business_rule_violation"

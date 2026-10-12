"""The error envelope every failed request returns."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    detail: str

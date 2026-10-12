"""Health check used by Docker Compose and CI smoke tests."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_db
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def read_health(db: Annotated[Session, Depends(get_db)]) -> HealthResponse:
    """Report healthy only if the database answers a trivial query."""
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ok")

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.v1.dependencies import MemberServiceDep
from app.api.v1.responses import error_responses
from app.schemas.members import MemberPage, MemberSort
from app.schemas.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix="/members", tags=["members"])


@router.get("", response_model=MemberPage, responses=error_responses(422))
def list_members(
    service: MemberServiceDep,
    q: Annotated[str | None, Query(max_length=100, description="Search by name.")] = None,
    sort: MemberSort = MemberSort.NAME,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> MemberPage:
    """List band members. Open to everyone, because the user picker needs it before login."""
    return service.list_members(q=q, sort=sort, page=page, page_size=page_size)

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.v1.dependencies import ActingMember, MemberServiceDep
from app.api.v1.responses import error_responses
from app.schemas.members import MemberPage, MemberProfile, MemberProfileUpdate, MemberSort
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


@router.get("/{member_id}", response_model=MemberProfile, responses=error_responses(403, 404, 422))
def get_member(member_id: int, actor: ActingMember, service: MemberServiceDep) -> MemberProfile:
    """A member's profile. Phone and email are only filled in for that member, the manager
    and the band leader."""
    return service.get_profile(actor, member_id)


@router.patch(
    "/{member_id}", response_model=MemberProfile, responses=error_responses(403, 404, 409, 422)
)
def update_member(
    member_id: int, body: MemberProfileUpdate, actor: ActingMember, service: MemberServiceDep
) -> MemberProfile:
    """Edit your own profile. Roles can't be changed."""
    return service.update_profile(actor, member_id, body)

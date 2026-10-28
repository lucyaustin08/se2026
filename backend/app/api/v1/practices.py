from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from pydantic import AwareDatetime

from app.api.v1.dependencies import ActingMember, PracticeServiceDep
from app.api.v1.responses import error_responses
from app.schemas.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.practices import PracticeCreate, PracticeOut, PracticePage, PracticeSort

router = APIRouter(prefix="/practices", tags=["practices"])


@router.get("", response_model=PracticePage, responses=error_responses(403, 422))
def list_practices(
    actor: ActingMember,
    service: PracticeServiceDep,
    q: Annotated[
        str | None, Query(max_length=100, description="Search the location and notes.")
    ] = None,
    starts_after: Annotated[
        AwareDatetime | None, Query(description="Only practices starting at or after this.")
    ] = None,
    starts_before: Annotated[
        AwareDatetime | None, Query(description="Only practices starting before this.")
    ] = None,
    sort: PracticeSort = PracticeSort.STARTS_AT,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PracticePage:
    """The manager and band leader see every practice; members see the ones they're invited
    to."""
    return service.list_practices(
        actor,
        q=q,
        starts_after=starts_after,
        starts_before=starts_before,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.post(
    "", status_code=201, response_model=PracticeOut, responses=error_responses(403, 409, 422)
)
def schedule_practice(
    body: PracticeCreate,
    actor: ActingMember,
    service: PracticeServiceDep,
    request: Request,
    response: Response,
) -> PracticeOut:
    """Schedule a one-time practice (manager or band leader).

    Refused if it overlaps a gig. If a gig is on the same day, it's refused unless
    `confirm_same_day` is true.
    """
    practice = service.schedule(actor, body)
    response.headers["Location"] = request.app.url_path_for("get_practice", practice_id=practice.id)
    return practice


@router.get("/{practice_id}", response_model=PracticeOut, responses=error_responses(403, 404, 422))
def get_practice(practice_id: int, actor: ActingMember, service: PracticeServiceDep) -> PracticeOut:
    return service.get_practice(actor, practice_id)


@router.post(
    "/{practice_id}/accept",
    response_model=PracticeOut,
    responses=error_responses(403, 404, 409, 422),
)
def accept_practice(
    practice_id: int, actor: ActingMember, service: PracticeServiceDep
) -> PracticeOut:
    """Say you'll be at a practice you're invited to."""
    return service.answer(actor, practice_id, accept=True)


@router.post(
    "/{practice_id}/decline",
    response_model=PracticeOut,
    responses=error_responses(403, 404, 409, 422),
)
def decline_practice(
    practice_id: int, actor: ActingMember, service: PracticeServiceDep
) -> PracticeOut:
    """Say you can't make a practice you're invited to."""
    return service.answer(actor, practice_id, accept=False)

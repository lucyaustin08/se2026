from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from pydantic import AwareDatetime

from app.api.v1.dependencies import ActingMember, AvailabilityServiceDep
from app.api.v1.responses import error_responses
from app.schemas.availability import BusyTimeIn, BusyTimeOut, BusyTimePage, BusyTimeSort
from app.schemas.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix="/busy-times", tags=["availability"])


@router.get("", response_model=BusyTimePage, responses=error_responses(403, 422))
def list_busy_times(
    actor: ActingMember,
    service: AvailabilityServiceDep,
    member_id: Annotated[int | None, Query(description="Only this member's busy times.")] = None,
    ends_after: Annotated[
        AwareDatetime | None, Query(description="Only busy times that end after this moment.")
    ] = None,
    starts_before: Annotated[
        AwareDatetime | None,
        Query(description="Only busy times that start before this moment."),
    ] = None,
    sort: BusyTimeSort = BusyTimeSort.STARTS_AT,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> BusyTimePage:
    """Busy times. The manager and band leader see everyone's; members see only their own.

    There's no `q`: a busy time has no text to search, because members don't give a reason.
    """
    return service.list_busy_times(
        actor,
        member_id=member_id,
        ends_after=ends_after,
        starts_before=starts_before,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.post("", status_code=201, response_model=BusyTimeOut, responses=error_responses(403, 422))
def add_busy_time(
    body: BusyTimeIn,
    actor: ActingMember,
    service: AvailabilityServiceDep,
    request: Request,
    response: Response,
) -> BusyTimeOut:
    """Add a one-off busy time for yourself."""
    busy_time = service.add_busy_time(actor, body)
    response.headers["Location"] = request.app.url_path_for(
        "change_busy_time", busy_time_id=busy_time.id
    )
    return busy_time


@router.patch(
    "/{busy_time_id}", response_model=BusyTimeOut, responses=error_responses(403, 404, 422)
)
def change_busy_time(
    busy_time_id: int, body: BusyTimeIn, actor: ActingMember, service: AvailabilityServiceDep
) -> BusyTimeOut:
    """Change one of your busy times. Send both times."""
    return service.change_busy_time(actor, busy_time_id, body)


@router.delete("/{busy_time_id}", status_code=204, responses=error_responses(403, 404, 422))
def delete_busy_time(
    busy_time_id: int, actor: ActingMember, service: AvailabilityServiceDep
) -> None:
    """Delete one of your busy times."""
    service.delete_busy_time(actor, busy_time_id)

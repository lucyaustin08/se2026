from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.api.v1.dependencies import ActingMember, AvailabilityServiceDep
from app.api.v1.responses import error_responses
from app.schemas.availability import (
    RecurringBusyTimeIn,
    RecurringBusyTimeOut,
    RecurringBusyTimePage,
    RecurringBusyTimeSort,
)
from app.schemas.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix="/recurring-busy-times", tags=["availability"])


@router.get("", response_model=RecurringBusyTimePage, responses=error_responses(403, 422))
def list_recurring_busy_times(
    actor: ActingMember,
    service: AvailabilityServiceDep,
    member_id: Annotated[int | None, Query(description="Only this member's.")] = None,
    sort: RecurringBusyTimeSort = RecurringBusyTimeSort.STARTS_ON,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> RecurringBusyTimePage:
    """Weekly busy times. The manager and band leader see everyone's; members see only their
    own. There's no `q`: a weekly busy time has no text to search."""
    return service.list_recurring(
        actor, member_id=member_id, sort=sort, page=page, page_size=page_size
    )


@router.post(
    "",
    status_code=201,
    response_model=RecurringBusyTimeOut,
    responses=error_responses(403, 422),
)
def add_recurring_busy_time(
    body: RecurringBusyTimeIn,
    actor: ActingMember,
    service: AvailabilityServiceDep,
    request: Request,
    response: Response,
) -> RecurringBusyTimeOut:
    """Add a weekly busy time for yourself, in the band's local clock time."""
    rule = service.add_recurring(actor, body)
    response.headers["Location"] = request.app.url_path_for(
        "change_recurring_busy_time", rule_id=rule.id
    )
    return rule


@router.patch(
    "/{rule_id}",
    response_model=RecurringBusyTimeOut,
    responses=error_responses(403, 404, 422),
)
def change_recurring_busy_time(
    rule_id: int, body: RecurringBusyTimeIn, actor: ActingMember, service: AvailabilityServiceDep
) -> RecurringBusyTimeOut:
    """Change one of your weekly busy times. Send every field."""
    return service.change_recurring(actor, rule_id, body)


@router.delete("/{rule_id}", status_code=204, responses=error_responses(403, 404, 422))
def delete_recurring_busy_time(
    rule_id: int, actor: ActingMember, service: AvailabilityServiceDep
) -> None:
    """Delete one of your weekly busy times."""
    service.delete_recurring(actor, rule_id)

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.api.v1.dependencies import ActingMember, GigServiceDep
from app.api.v1.responses import error_responses
from app.models.enums import GigStatus
from app.schemas.gigs import (
    GigCreate,
    GigDetail,
    GigPage,
    GigSort,
    GigUpdate,
    InvitationIn,
    SlotPayIn,
)
from app.schemas.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix="/gigs", tags=["gigs"])


@router.get("", response_model=GigPage, responses=error_responses(403, 422))
def list_gigs(
    actor: ActingMember,
    service: GigServiceDep,
    q: Annotated[
        str | None, Query(max_length=100, description="Search venue and contact names.")
    ] = None,
    sort: GigSort = GigSort.FIRST_SET_AT,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    status: GigStatus | None = None,
    has_date: Annotated[
        bool | None, Query(description="true: only dated gigs. false: only undated drafts.")
    ] = None,
) -> GigPage:
    return service.list_gigs(
        actor,
        q=q,
        status=status,
        has_date=has_date,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    status_code=201,
    response_model=GigDetail,
    responses=error_responses(403, 409, 422),
)
def create_gig(
    body: GigCreate,
    actor: ActingMember,
    service: GigServiceDep,
    request: Request,
    response: Response,
) -> GigDetail:
    gig = service.create_gig(actor, body)
    response.headers["Location"] = request.app.url_path_for("get_gig", gig_id=gig.id)
    return gig


@router.get("/{gig_id}", response_model=GigDetail, responses=error_responses(403, 404, 422))
def get_gig(gig_id: int, actor: ActingMember, service: GigServiceDep) -> GigDetail:
    return service.get_gig(actor, gig_id)


@router.patch("/{gig_id}", response_model=GigDetail, responses=error_responses(403, 404, 409, 422))
def update_gig(
    gig_id: int, body: GigUpdate, actor: ActingMember, service: GigServiceDep
) -> GigDetail:
    return service.update_gig(actor, gig_id, body)


@router.post(
    "/{gig_id}/book", response_model=GigDetail, responses=error_responses(403, 404, 409, 422)
)
def book_gig(gig_id: int, actor: ActingMember, service: GigServiceDep) -> GigDetail:
    return service.book_gig(actor, gig_id)


# ---- Lineup slots ------------------------------------------------------------------------


@router.post(
    "/{gig_id}/slots/{slot_id}/invite",
    response_model=GigDetail,
    responses=error_responses(403, 404, 409, 422),
)
def invite_to_slot(
    gig_id: int, slot_id: int, body: InvitationIn, actor: ActingMember, service: GigServiceDep
) -> GigDetail:
    """Invite a member to fill a slot (manager only). Replaces a pending or declined invite."""
    return service.invite(actor, gig_id, slot_id, body)


@router.patch(
    "/{gig_id}/slots/{slot_id}",
    response_model=GigDetail,
    responses=error_responses(403, 404, 422),
)
def set_slot_pay(
    gig_id: int, slot_id: int, body: SlotPayIn, actor: ActingMember, service: GigServiceDep
) -> GigDetail:
    """Change what the member in this slot is paid (manager only)."""
    return service.set_slot_pay(actor, gig_id, slot_id, body.pay_cents)


@router.post(
    "/{gig_id}/slots/{slot_id}/accept",
    response_model=GigDetail,
    responses=error_responses(403, 404, 409, 422),
)
def accept_invitation(
    gig_id: int, slot_id: int, actor: ActingMember, service: GigServiceDep
) -> GigDetail:
    """Accept your own invitation. Refused if it overlaps another gig you accepted."""
    return service.accept(actor, gig_id, slot_id)


@router.post(
    "/{gig_id}/slots/{slot_id}/decline",
    response_model=GigDetail,
    responses=error_responses(403, 404, 409, 422),
)
def decline_invitation(
    gig_id: int, slot_id: int, actor: ActingMember, service: GigServiceDep
) -> GigDetail:
    """Decline your own invitation."""
    return service.decline(actor, gig_id, slot_id)

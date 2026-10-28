"""Shared FastAPI dependencies."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session, sessionmaker

from app.models.member import Member
from app.services.availability import AvailabilityService
from app.services.gigs import GigService
from app.services.members import MemberService

ACTING_MEMBER_HEADER = "X-Acting-Member-Id"


def get_db(request: Request) -> Iterator[Session]:
    """Open one database session for the request and close it afterwards."""
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]


def get_acting_member(
    db: DbSession,
    acting_member_id: Annotated[
        int | None,
        Header(
            alias=ACTING_MEMBER_HEADER,
            description="Who is using the app, chosen with the sprint 1 user picker.",
        ),
    ] = None,
) -> Member:
    return MemberService(db).get_actor(acting_member_id)


def get_availability_service(db: DbSession) -> AvailabilityService:
    return AvailabilityService(db)


def get_gig_service(db: DbSession) -> GigService:
    return GigService(db)


def get_member_service(db: DbSession) -> MemberService:
    return MemberService(db)


ActingMember = Annotated[Member, Depends(get_acting_member)]
AvailabilityServiceDep = Annotated[AvailabilityService, Depends(get_availability_service)]
GigServiceDep = Annotated[GigService, Depends(get_gig_service)]
MemberServiceDep = Annotated[MemberService, Depends(get_member_service)]

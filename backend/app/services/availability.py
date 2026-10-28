"""Busy times, and who is free to play a gig."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.availability import BusyTime
from app.models.member import Member
from app.repositories.availability import BusyTimeRepository
from app.repositories.gigs import GigRepository
from app.repositories.members import MemberRepository
from app.schemas.availability import (
    BusyTimeIn,
    BusyTimeOut,
    BusyTimePage,
    BusyTimeSort,
    Conflict,
    ConflictKind,
    GigAvailability,
    PlayerAvailability,
)
from app.schemas.members import MemberSummary
from app.services.gigs import busy_window
from app.services.permissions import require_runs_the_band, runs_the_band


class AvailabilityService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._busy_times = BusyTimeRepository(session)
        self._gigs = GigRepository(session)
        self._members = MemberRepository(session)

    # ---- Busy times --------------------------------------------------------------------------

    def list_busy_times(
        self,
        actor: Member,
        *,
        member_id: int | None,
        ends_after: datetime | None,
        starts_before: datetime | None,
        sort: BusyTimeSort,
        page: int,
        page_size: int,
    ) -> BusyTimePage:
        """The manager and band leader see everyone's busy times. Members see only their own."""
        if not runs_the_band(actor):
            if member_id is not None and member_id != actor.id:
                raise PermissionDeniedError(
                    "Only the manager and band leader can see other members' availability.",
                    code="availability_private",
                )
            member_id = actor.id
        busy_times, total = self._busy_times.search(
            member_id=member_id,
            ends_after=ends_after,
            starts_before=starts_before,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return BusyTimePage(
            items=[_busy_time_out(busy_time) for busy_time in busy_times],
            total=total,
            page=page,
            page_size=page_size,
        )

    def add_busy_time(self, actor: Member, data: BusyTimeIn) -> BusyTimeOut:
        """A member adds a busy time for themselves."""
        busy_time = self._busy_times.add(
            BusyTime(member_id=actor.id, starts_at=data.starts_at, ends_at=data.ends_at)
        )
        self._session.commit()
        self._session.refresh(busy_time)
        return _busy_time_out(busy_time)

    def change_busy_time(self, actor: Member, busy_time_id: int, data: BusyTimeIn) -> BusyTimeOut:
        busy_time = self._own_busy_time(actor, busy_time_id)
        busy_time.starts_at = data.starts_at
        busy_time.ends_at = data.ends_at
        self._session.commit()
        return _busy_time_out(busy_time)

    def delete_busy_time(self, actor: Member, busy_time_id: int) -> None:
        self._busy_times.delete(self._own_busy_time(actor, busy_time_id))
        self._session.commit()

    # ---- Who can play a gig ------------------------------------------------------------------

    def gig_availability(self, actor: Member, gig_id: int) -> GigAvailability:
        require_runs_the_band(actor, "see who's available")
        gig = self._gigs.get(gig_id)
        if gig is None:
            raise NotFoundError("That gig doesn't exist.", code="gig_not_found")
        window = busy_window(gig)
        players = self._members.players()
        if window is None:
            return GigAvailability(
                window_starts_at=None,
                window_ends_at=None,
                players=[_player(member, []) for member in players],
            )
        start, end = window
        return GigAvailability(
            window_starts_at=start,
            window_ends_at=end,
            players=[
                _player(member, self._conflicts(member, gig.id, start, end)) for member in players
            ],
        )

    def _conflicts(
        self, member: Member, gig_id: int, start: datetime, end: datetime
    ) -> list[Conflict]:
        conflicts = [
            Conflict(
                kind=ConflictKind.BUSY_TIME,
                starts_at=busy_time.starts_at,
                ends_at=busy_time.ends_at,
                gig_id=None,
                venue_name=None,
            )
            for busy_time in self._busy_times.overlapping(member.id, start, end)
        ]
        for other in self._gigs.accepted_by_member(member.id, exclude_gig_id=gig_id):
            other_window = busy_window(other)
            if other_window is not None and other_window[0] < end and start < other_window[1]:
                conflicts.append(
                    Conflict(
                        kind=ConflictKind.GIG,
                        starts_at=other_window[0],
                        ends_at=other_window[1],
                        gig_id=other.id,
                        venue_name=other.venue_name,
                    )
                )
        return sorted(conflicts, key=lambda conflict: conflict.starts_at)

    def _own_busy_time(self, actor: Member, busy_time_id: int) -> BusyTime:
        busy_time = self._busy_times.get(busy_time_id)
        if busy_time is None:
            raise NotFoundError("That busy time doesn't exist.", code="busy_time_not_found")
        if busy_time.member_id != actor.id:
            raise PermissionDeniedError(
                "You can only change your own busy times.", code="not_your_busy_time"
            )
        return busy_time


def _busy_time_out(busy_time: BusyTime) -> BusyTimeOut:
    return BusyTimeOut(
        id=busy_time.id,
        member=MemberSummary.model_validate(busy_time.member),
        starts_at=busy_time.starts_at,
        ends_at=busy_time.ends_at,
        created_at=busy_time.created_at,
    )


def _player(member: Member, conflicts: list[Conflict]) -> PlayerAvailability:
    return PlayerAvailability(
        member=MemberSummary.model_validate(member),
        primary_role=member.primary_role,
        secondary_role=member.secondary_role,
        busy=bool(conflicts),
        conflicts=conflicts,
    )

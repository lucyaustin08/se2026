"""Scheduling practices, and members answering their invitations."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleViolation, NotFoundError
from app.models.enums import InvitationStatus
from app.models.gig import Gig
from app.models.member import Member
from app.models.practice import Practice, PracticeInvitation
from app.repositories.availability import BusyTimeRepository
from app.repositories.gigs import GigRepository
from app.repositories.members import MemberRepository
from app.repositories.practices import PracticeRepository
from app.schemas.members import MemberSummary
from app.schemas.practices import (
    PracticeCreate,
    PracticeInvitationOut,
    PracticeOut,
    PracticePage,
    PracticeSort,
    PracticeSuggestionQuery,
    PracticeSuggestions,
    SuggestedTime,
)
from app.services.band_time import BAND_TIME_ZONE, band_date
from app.services.gigs import busy_window
from app.services.permissions import require_runs_the_band, runs_the_band

# Practices are usually planned one to three weeks ahead (product owner), so that's where
# suggestions come from.
SUGGEST_FROM_DAYS = 7
SUGGEST_TO_DAYS = 21
SUGGESTION_STEP_MINUTES = 30

# How far either side of a practice to look for gigs. A gig's soundcheck and end can be up to
# 12 hours from its first set, and "same day" needs the whole local day.
_GIG_SEARCH_MARGIN = timedelta(days=2)


class PracticeService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._practices = PracticeRepository(session)
        self._gigs = GigRepository(session)
        self._members = MemberRepository(session)
        self._busy_times = BusyTimeRepository(session)

    # ---- Reading -----------------------------------------------------------------------------

    def list_practices(
        self,
        actor: Member,
        *,
        q: str | None,
        starts_after: datetime | None,
        starts_before: datetime | None,
        sort: PracticeSort,
        page: int,
        page_size: int,
    ) -> PracticePage:
        """The manager and band leader see every practice. Members see the ones they're
        invited to, whatever their answer."""
        practices, total = self._practices.search(
            q=q,
            invited_member_id=None if runs_the_band(actor) else actor.id,
            starts_after=starts_after,
            starts_before=starts_before,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return PracticePage(
            items=[_practice_out(actor, practice) for practice in practices],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_practice(self, actor: Member, practice_id: int) -> PracticeOut:
        return _practice_out(actor, self._visible_or_404(actor, practice_id))

    # ---- Scheduling --------------------------------------------------------------------------

    def schedule(self, actor: Member, data: PracticeCreate) -> PracticeOut:
        require_runs_the_band(actor, "schedule practices")
        invitees = self._invitees(data.member_ids)
        start = data.starts_at
        end = start + timedelta(minutes=data.length_minutes)

        nearby = self._gigs.dated_between(start - _GIG_SEARCH_MARGIN, end + _GIG_SEARCH_MARGIN)
        for gig in nearby:
            window = busy_window(gig)
            if window is not None and window[0] < end and start < window[1]:
                raise BusinessRuleViolation(
                    f"This practice overlaps {_describe(gig)}. Pick a time that's clear of it.",
                    code="practice_overlaps_gig",
                )
        if not data.confirm_same_day:
            practice_days = {band_date(start), band_date(end - timedelta(microseconds=1))}
            same_day = [
                gig
                for gig in nearby
                if gig.first_set_at is not None and band_date(gig.first_set_at) in practice_days
            ]
            if same_day:
                raise BusinessRuleViolation(
                    f"There's a gig the same day: {_describe(same_day[0])}. "
                    "Schedule the practice anyway?",
                    code="practice_same_day_as_gig",
                )

        now = datetime.now(UTC)
        practice = Practice(
            starts_at=start,
            length_minutes=data.length_minutes,
            location=data.location,
            notes=data.notes,
            scheduled_by_id=actor.id,
            invitations=[
                # Whoever schedules a practice they're playing in is already coming.
                PracticeInvitation(
                    member_id=member.id,
                    status=InvitationStatus.ACCEPTED
                    if member.id == actor.id
                    else InvitationStatus.INVITED,
                    responded_at=now if member.id == actor.id else None,
                )
                for member in invitees
            ],
        )
        self._practices.add(practice)
        self._session.commit()
        self._session.refresh(practice)
        return _practice_out(actor, practice)

    # ---- Finding a time ----------------------------------------------------------------------

    def suggest_times(
        self, actor: Member, query: PracticeSuggestionQuery, *, today: date | None = None
    ) -> PracticeSuggestions:
        """The best time on each day one to three weeks ahead, best days first.

        A time is never suggested if it overlaps a booked or pending gig. An invitee can't
        come if one of their busy times, or another practice they haven't declined, overlaps.
        """
        require_runs_the_band(actor, "find practice times")
        invitees = self._invitees(query.member_ids)
        today = today or band_date(datetime.now(UTC))
        first_day = today + timedelta(days=SUGGEST_FROM_DAYS)
        last_day = today + timedelta(days=SUGGEST_TO_DAYS)
        search_start = _band_moment(first_day, query.earliest)
        search_end = _band_moment(last_day, query.latest)

        gigs = self._gigs.dated_between(
            search_start - _GIG_SEARCH_MARGIN, search_end + _GIG_SEARCH_MARGIN
        )
        gig_windows = [window for gig in gigs if (window := busy_window(gig)) is not None]
        busy = {
            member.id: self._member_busy_periods(member, search_start, search_end)
            for member in invitees
        }
        length = timedelta(minutes=query.length_minutes)
        earliest = query.earliest.hour * 60 + query.earliest.minute
        latest = query.latest.hour * 60 + query.latest.minute

        suggestions: list[SuggestedTime] = []
        for offset in range((last_day - first_day).days + 1):
            day = first_day + timedelta(days=offset)
            best: SuggestedTime | None = None
            for minute in range(
                earliest, latest - query.length_minutes + 1, SUGGESTION_STEP_MINUTES
            ):
                start = _band_moment(day, time(minute // 60, minute % 60))
                end = start + length
                if any(s < end and start < e for s, e in gig_windows):
                    continue
                free = [
                    m for m in invitees if not any(s < end and start < e for s, e in busy[m.id])
                ]
                if best is None or len(free) > len(best.available):
                    best = SuggestedTime(
                        starts_at=start,
                        ends_at=end,
                        available=[MemberSummary.model_validate(m) for m in free],
                        unavailable=[
                            MemberSummary.model_validate(m) for m in invitees if m not in free
                        ],
                        same_day_gig=next(
                            (
                                _describe(gig)
                                for gig in gigs
                                if gig.first_set_at is not None
                                and band_date(gig.first_set_at) == day
                            ),
                            None,
                        ),
                    )
            if best is not None:
                suggestions.append(best)

        suggestions.sort(key=lambda s: (-len(s.available), s.starts_at))
        return PracticeSuggestions(
            searched_from=first_day, searched_to=last_day, suggestions=suggestions
        )

    def _member_busy_periods(
        self, member: Member, start: datetime, end: datetime
    ) -> list[tuple[datetime, datetime]]:
        """When a member can't come to a practice: their busy times, and other practices they
        haven't declined."""
        periods = [
            (b.starts_at, b.ends_at) for b in self._busy_times.overlapping(member.id, start, end)
        ]
        periods += [
            (p.starts_at, p.ends_at)
            for p in self._practices.overlapping_for_member(member.id, start, end)
        ]
        return periods

    # ---- Answering ---------------------------------------------------------------------------

    def answer(self, actor: Member, practice_id: int, *, accept: bool) -> PracticeOut:
        practice = self._visible_or_404(actor, practice_id)
        invitation = practice.invitation_for(actor.id)
        if invitation is None:
            raise NotFoundError(
                "You aren't invited to this practice.", code="practice_invitation_not_found"
            )
        if invitation.status is not InvitationStatus.INVITED:
            raise BusinessRuleViolation(
                f"You've already answered this invitation ({invitation.status.value}).",
                code="invitation_not_pending",
            )
        invitation.status = InvitationStatus.ACCEPTED if accept else InvitationStatus.DECLINED
        invitation.responded_at = datetime.now(UTC)
        self._session.commit()
        return _practice_out(actor, practice)

    # ---- Helpers -----------------------------------------------------------------------------

    def _invitees(self, member_ids: list[int]) -> list[Member]:
        members: list[Member] = []
        for member_id in dict.fromkeys(member_ids):  # drop repeats, keep order
            member = self._members.get(member_id)
            if member is None:
                raise BusinessRuleViolation(
                    f"There's no member with id {member_id}.", code="unknown_member"
                )
            if member.is_manager:
                raise BusinessRuleViolation(
                    "The manager doesn't play, so can't be invited to practice.",
                    code="manager_cannot_play",
                )
            members.append(member)
        return members

    def _visible_or_404(self, actor: Member, practice_id: int) -> Practice:
        practice = self._practices.get(practice_id)
        # A practice a member isn't invited to looks the same as one that doesn't exist.
        if practice is None or not (
            runs_the_band(actor) or practice.invitation_for(actor.id) is not None
        ):
            raise NotFoundError("That practice doesn't exist.", code="practice_not_found")
        return practice


def _band_moment(day: date, at: time) -> datetime:
    """A local wall-clock time on a day at the band's location, as a UTC moment."""
    return datetime.combine(day, at, tzinfo=BAND_TIME_ZONE).astimezone(UTC)


def _describe(gig: Gig) -> str:
    """Like "Hub City Tap on Mon, Nov 2 at 8:00 PM", in the band's time zone."""
    name = gig.venue_name or "an untitled gig"
    if gig.first_set_at is None:
        return name
    local = gig.first_set_at.astimezone(BAND_TIME_ZONE)
    hour = local.strftime("%I").lstrip("0")
    return f"{name} on {local:%a, %b} {local.day} at {hour}:{local:%M %p}"


def _practice_out(actor: Member, practice: Practice) -> PracticeOut:
    mine = practice.invitation_for(actor.id)
    return PracticeOut(
        id=practice.id,
        starts_at=practice.starts_at,
        ends_at=practice.ends_at,
        length_minutes=practice.length_minutes,
        location=practice.location,
        notes=practice.notes,
        scheduled_by=MemberSummary.model_validate(practice.scheduled_by),
        invitations=[
            PracticeInvitationOut(
                member=MemberSummary.model_validate(invitation.member),
                status=invitation.status,
                responded_at=invitation.responded_at,
            )
            for invitation in practice.invitations
        ],
        my_status=mine.status if mine else None,
        created_at=practice.created_at,
    )

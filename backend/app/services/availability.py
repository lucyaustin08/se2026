"""Busy times, and who is free to play a gig."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import BAND_TIME_ZONE_NAME
from app.core.errors import (
    AppError,
    BusinessRuleViolation,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.availability import BusyTime, RecurringBusyTime
from app.models.enums import InvitationStatus, SlotStatus
from app.models.gig import GigSlot
from app.models.member import Member
from app.models.practice import PracticeInvitation
from app.repositories.availability import BusyTimeRepository, RecurringBusyTimeRepository
from app.repositories.gigs import GigRepository
from app.repositories.members import MemberRepository
from app.repositories.practices import PracticeRepository
from app.schemas.availability import (
    BusyPeriod,
    BusyPeriodKind,
    BusyPeriods,
    BusyPeriodsQuery,
    BusyTimeIn,
    BusyTimeOut,
    BusyTimePage,
    BusyTimeSort,
    Conflict,
    ConflictKind,
    GigAvailability,
    PlayerAvailability,
    RecurringBusyTimeIn,
    RecurringBusyTimeOut,
    RecurringBusyTimePage,
    RecurringBusyTimeSort,
)
from app.schemas.members import MemberSummary
from app.services.band_time import describe_moment
from app.services.gigs import busy_window
from app.services.permissions import require_runs_the_band, runs_the_band


class AvailabilityService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._busy_times = BusyTimeRepository(session)
        self._recurring = RecurringBusyTimeRepository(session)
        self._gigs = GigRepository(session)
        self._members = MemberRepository(session)
        self._practices = PracticeRepository(session)

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
        """A member adds a busy time for themselves. See `_settle_commitments` for what
        happens when it overlaps a practice or gig they're invited to."""
        span = (data.starts_at, data.ends_at)
        self._settle_commitments(actor, lambda _start, _end: [span], data.decline_invitations)
        busy_time = self._busy_times.add(
            BusyTime(member_id=actor.id, starts_at=data.starts_at, ends_at=data.ends_at)
        )
        self._session.commit()
        self._session.refresh(busy_time)
        return _busy_time_out(busy_time)

    def change_busy_time(self, actor: Member, busy_time_id: int, data: BusyTimeIn) -> BusyTimeOut:
        busy_time = self._own_busy_time(actor, busy_time_id)
        span = (data.starts_at, data.ends_at)
        self._settle_commitments(actor, lambda _start, _end: [span], data.decline_invitations)
        busy_time.starts_at = data.starts_at
        busy_time.ends_at = data.ends_at
        self._session.commit()
        return _busy_time_out(busy_time)

    def delete_busy_time(self, actor: Member, busy_time_id: int) -> None:
        self._busy_times.delete(self._own_busy_time(actor, busy_time_id))
        self._session.commit()

    # ---- Weekly busy times ----------------------------------------------------------------------

    def list_recurring(
        self,
        actor: Member,
        *,
        member_id: int | None,
        sort: RecurringBusyTimeSort,
        page: int,
        page_size: int,
    ) -> RecurringBusyTimePage:
        """Same visibility as one-off busy times."""
        member_id = self._visible_member(actor, member_id)
        rules, total = self._recurring.search(
            member_id=member_id, sort=sort, page=page, page_size=page_size
        )
        return RecurringBusyTimePage(
            items=[_recurring_out(rule) for rule in rules],
            total=total,
            page=page,
            page_size=page_size,
        )

    def add_recurring(self, actor: Member, data: RecurringBusyTimeIn) -> RecurringBusyTimeOut:
        rule = RecurringBusyTime(member_id=actor.id, time_zone=BAND_TIME_ZONE_NAME)
        self._save_recurring(actor, rule, data)
        self._session.refresh(rule)
        return _recurring_out(rule)

    def change_recurring(
        self, actor: Member, rule_id: int, data: RecurringBusyTimeIn
    ) -> RecurringBusyTimeOut:
        rule = self._own_recurring(actor, rule_id)
        self._save_recurring(actor, rule, data)
        return _recurring_out(rule)

    def _save_recurring(
        self, actor: Member, rule: RecurringBusyTime, data: RecurringBusyTimeIn
    ) -> None:
        """Write the rule's new values and check them against the member's practices and
        gigs. PostgreSQL works out the rule's days, so the new values are flushed first and
        thrown away again if a rule refuses them."""
        rule.weekdays = data.weekdays
        rule.start_time = data.start_time
        rule.end_time = data.end_time
        rule.starts_on = data.starts_on
        rule.ends_on = data.ends_on
        self._recurring.add(rule)  # A new rule is added; a changed one is already there.

        def days_of_rule(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
            return [
                (o.starts_at, o.ends_at)
                for o in self._recurring.occurrences(start, end, member_ids=[actor.id])
                if o.rule_id == rule.id
            ]

        try:
            self._settle_commitments(actor, days_of_rule, data.decline_invitations)
        except AppError:
            self._session.rollback()
            raise
        self._session.commit()

    def delete_recurring(self, actor: Member, rule_id: int) -> None:
        self._recurring.delete(self._own_recurring(actor, rule_id))
        self._session.commit()

    # ---- Every busy period in a range, for the calendar --------------------------------------

    def busy_periods(self, actor: Member, query: BusyPeriodsQuery) -> BusyPeriods:
        """One-off busy times and each day of the weekly ones that overlap the range. The
        manager and band leader see everyone's; members see only their own."""
        start, end = query.ends_after, query.starts_before
        member_ids = None if runs_the_band(actor) else [actor.id]
        periods = [
            BusyPeriod(
                kind=BusyPeriodKind.ONE_OFF,
                source_id=busy_time.id,
                member=MemberSummary.model_validate(busy_time.member),
                starts_at=busy_time.starts_at,
                ends_at=busy_time.ends_at,
            )
            for busy_time in self._busy_times.overlapping_any(start, end, member_ids=member_ids)
        ]
        names = {m.id: m for m in self._members.players()}
        for occurrence in self._recurring.occurrences(start, end, member_ids=member_ids):
            member = names.get(occurrence.member_id)
            periods.append(
                BusyPeriod(
                    kind=BusyPeriodKind.WEEKLY,
                    source_id=occurrence.rule_id,
                    member=MemberSummary(
                        id=occurrence.member_id, name=member.name if member else ""
                    ),
                    starts_at=occurrence.starts_at,
                    ends_at=occurrence.ends_at,
                )
            )
        periods.sort(key=lambda p: (p.starts_at, p.kind, p.source_id))
        return BusyPeriods(ends_after=start, starts_before=end, periods=periods)

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
        conflicts += [
            Conflict(
                kind=ConflictKind.WEEKLY_BUSY_TIME,
                starts_at=occurrence.starts_at,
                ends_at=occurrence.ends_at,
                gig_id=None,
                venue_name=None,
            )
            for occurrence in self._recurring.occurrences(start, end, member_ids=[member.id])
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

    # ---- Busy times over practices and gigs ----------------------------------------------------

    def _settle_commitments(
        self,
        actor: Member,
        spans_between: Callable[[datetime, datetime], list[tuple[datetime, datetime]]],
        decline_invitations: bool,
    ) -> None:
        """A busy time can't overlap a practice or gig the member has accepted (409
        `busy_time_overlaps_accepted`). If it overlaps ones they're only invited to, it's
        refused with a warning (409 `busy_time_overlaps_invitation`) until they confirm with
        `decline_invitations`, and then those invitations are declined.

        `spans_between(start, end)` gives the busy time's stretches between two moments. Only
        practices and gigs that haven't ended count; for gigs, soundcheck to the end."""
        commitments = self._open_commitments(actor)
        if not commitments:
            return
        spans = spans_between(
            min(c.starts_at for c in commitments), max(c.ends_at for c in commitments)
        )
        overlapping = [
            c for c in commitments if any(s < c.ends_at and c.starts_at < e for s, e in spans)
        ]
        accepted = [c for c in overlapping if c.accepted]
        if accepted:
            raise BusinessRuleViolation(
                f"You're attending {_join(c.description for c in accepted)} then, so you can't "
                "mark that time as busy. If you can't make it, talk to the manager or band "
                "leader.",
                code="busy_time_overlaps_accepted",
            )
        if not overlapping:
            return
        if not decline_invitations:
            it = "it" if len(overlapping) == 1 else "them"
            raise BusinessRuleViolation(
                f"You're invited to {_join(c.description for c in overlapping)} then. "
                f"Add the busy time anyway and decline {it}?",
                code="busy_time_overlaps_invitation",
            )
        now = datetime.now(UTC)
        for commitment in overlapping:
            commitment.decline(now)

    def _open_commitments(self, member: Member) -> list["_Commitment"]:
        """Practices and gigs the member is invited to or has accepted that haven't ended."""
        now = datetime.now(UTC)
        commitments: list[_Commitment] = []
        for invitation in self._practices.open_invitations_for_member(member.id, ending_after=now):
            practice = invitation.practice
            place = f" at {practice.location}" if practice.location else ""
            commitments.append(
                _Commitment(
                    starts_at=practice.starts_at,
                    ends_at=practice.ends_at,
                    accepted=invitation.status == InvitationStatus.ACCEPTED,
                    description=f"the practice{place} on {describe_moment(practice.starts_at)}",
                    decline=_decline_practice(invitation),
                )
            )
        for slot in self._gigs.open_slots_for_member(member.id):
            window = busy_window(slot.gig)
            if window is None or window[1] <= now:
                continue
            gig = slot.gig
            when = describe_moment(gig.first_set_at) if gig.first_set_at else ""
            commitments.append(
                _Commitment(
                    starts_at=window[0],
                    ends_at=window[1],
                    accepted=slot.status == SlotStatus.ACCEPTED,
                    description=f"{gig.venue_name or 'a gig'} on {when}",
                    decline=_decline_slot(slot),
                )
            )
        return commitments

    def _visible_member(self, actor: Member, member_id: int | None) -> int | None:
        """Whose busy times this actor may list: anyone's for the manager and band leader,
        only their own for everyone else."""
        if runs_the_band(actor):
            return member_id
        if member_id is not None and member_id != actor.id:
            raise PermissionDeniedError(
                "Only the manager and band leader can see other members' availability.",
                code="availability_private",
            )
        return actor.id

    def _own_recurring(self, actor: Member, rule_id: int) -> RecurringBusyTime:
        rule = self._recurring.get(rule_id)
        if rule is None:
            raise NotFoundError(
                "That weekly busy time doesn't exist.", code="recurring_busy_time_not_found"
            )
        if rule.member_id != actor.id:
            raise PermissionDeniedError(
                "You can only change your own busy times.", code="not_your_busy_time"
            )
        return rule

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


def _recurring_out(rule: RecurringBusyTime) -> RecurringBusyTimeOut:
    return RecurringBusyTimeOut(
        id=rule.id,
        member=MemberSummary.model_validate(rule.member),
        weekdays=list(rule.weekdays),
        start_time=rule.start_time,
        end_time=rule.end_time,
        starts_on=rule.starts_on,
        ends_on=rule.ends_on,
        time_zone=rule.time_zone,
        created_at=rule.created_at,
    )


def _player(member: Member, conflicts: list[Conflict]) -> PlayerAvailability:
    return PlayerAvailability(
        member=MemberSummary.model_validate(member),
        primary_role=member.primary_role,
        secondary_role=member.secondary_role,
        busy=bool(conflicts),
        conflicts=conflicts,
    )


@dataclass
class _Commitment:
    """A practice or gig a member is invited to or has accepted, from soundcheck or start to
    the end."""

    starts_at: datetime
    ends_at: datetime
    accepted: bool
    description: str
    decline: Callable[[datetime], None]


def _decline_practice(invitation: PracticeInvitation) -> Callable[[datetime], None]:
    def decline(now: datetime) -> None:
        invitation.status = InvitationStatus.DECLINED
        invitation.responded_at = now

    return decline


def _decline_slot(slot: GigSlot) -> Callable[[datetime], None]:
    def decline(now: datetime) -> None:
        slot.status = SlotStatus.DECLINED
        slot.responded_at = now

    return decline


def _join(names: Iterable[str]) -> str:
    """ "A", "A and B", "A, B and C"."""
    items = list(names)
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"

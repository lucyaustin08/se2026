"""Business rules for gigs: who can see and change them, invitations, and booking."""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import AppError, BusinessRuleViolation, NotFoundError, PermissionDeniedError
from app.models.enums import GigStatus, Role, SlotStatus
from app.models.gig import (
    DEFAULT_LOAD_IN_OFFSET_MINUTES,
    DEFAULT_PERFORMANCE_MINUTES,
    DEFAULT_SOUNDCHECK_OFFSET_MINUTES,
    Gig,
    GigContact,
    GigSlot,
)
from app.models.member import Member
from app.repositories.gigs import GigRepository, MemberSlotFilter
from app.repositories.members import MemberRepository
from app.schemas.gigs import (
    ContactIn,
    ContactOut,
    GigCreate,
    GigDetail,
    GigListItem,
    GigPage,
    GigSort,
    GigUpdate,
    InvitationIn,
    SlotOut,
)
from app.schemas.members import MemberSummary
from app.services.booking import missing_for_booking
from app.services.lineup import ROLE_LABELS, ROLE_ORDER, lineup_size

# Slots that let a member see a potential gig: they've been asked, or they said yes.
SLOT_STATUSES_THAT_SHOW_A_GIG = frozenset({SlotStatus.INVITED, SlotStatus.ACCEPTED})


class GigService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._gigs = GigRepository(session)
        self._members = MemberRepository(session)

    # ---- Reading ---------------------------------------------------------------------------

    def list_gigs(
        self,
        actor: Member,
        *,
        q: str | None,
        status: GigStatus | None,
        has_date: bool | None,
        sort: GigSort,
        page: int,
        page_size: int,
    ) -> GigPage:
        statuses: frozenset[GigStatus] | None
        member_slot: MemberSlotFilter | None
        if actor.is_manager:
            statuses = None if status is None else frozenset({status})
            member_slot = None
        else:
            # Members see booked gigs (other people's as restricted rows) and the potential
            # gigs they've been invited to. A search only covers gigs they hold a slot on,
            # because matching venue or contact names would reveal a restricted gig.
            visible = frozenset({GigStatus.BOOKED, GigStatus.POTENTIAL})
            statuses = visible if status is None else visible & {status}
            member_slot = MemberSlotFilter(
                member_id=actor.id,
                slot_statuses=SLOT_STATUSES_THAT_SHOW_A_GIG,
                except_gig_statuses=frozenset() if q else frozenset({GigStatus.BOOKED}),
            )

        gigs, total = self._gigs.search(
            q=q,
            statuses=statuses,
            has_date=has_date,
            member_slot=member_slot,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return GigPage(
            items=[self._to_list_item(actor, gig) for gig in gigs],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_gig(self, actor: Member, gig_id: int) -> GigDetail:
        gig = self._get_or_404(gig_id)
        self._require_can_view(actor, gig)
        return self._to_detail(actor, gig)

    # ---- Manager: creating and editing ------------------------------------------------------

    def create_gig(self, actor: Member, data: GigCreate) -> GigDetail:
        _require_manager(actor, "add gigs")
        gig = Gig(
            status=GigStatus.POTENTIAL,
            first_set_at=data.first_set_at,
            load_in_offset_minutes=data.load_in_offset_minutes,
            soundcheck_offset_minutes=data.soundcheck_offset_minutes,
            performance_minutes=data.performance_minutes,
            venue_name=data.venue_name,
            venue_address=data.venue_address,
            pay_cents=data.pay_cents,
            slots=[GigSlot(role=role, status=SlotStatus.OPEN) for role in data.roles],
            contacts=[_contact(contact) for contact in data.contacts],
        )
        self._gigs.add(gig)
        self._session.commit()
        return self._to_detail(actor, gig)

    def update_gig(self, actor: Member, gig_id: int, data: GigUpdate) -> GigDetail:
        _require_manager(actor, "edit gigs")
        gig = self._get_or_404(gig_id)
        return self._in_transaction(lambda: self._apply_update(actor, gig, data))

    def book_gig(self, actor: Member, gig_id: int) -> GigDetail:
        _require_manager(actor, "book gigs")
        gig = self._get_or_404(gig_id)
        _require_potential(gig)
        _require_complete(gig, "This gig can't be booked until it has:")
        gig.status = GigStatus.BOOKED
        self._session.commit()
        return self._to_detail(actor, gig)

    # ---- Manager: invitations and pay --------------------------------------------------------

    def invite(self, actor: Member, gig_id: int, slot_id: int, data: InvitationIn) -> GigDetail:
        _require_manager(actor, "invite members")
        gig = self._get_or_404(gig_id)
        slot = _slot_or_404(gig, slot_id)
        _require_potential(gig)
        if slot.status is SlotStatus.ACCEPTED:
            raise BusinessRuleViolation(
                f"{_member_name(slot)} already accepted this slot.", code="slot_already_filled"
            )
        member = self._members.get(data.member_id)
        if member is None:
            raise BusinessRuleViolation(
                f"There is no member with id {data.member_id}.", code="unknown_member"
            )
        if member.is_manager:
            raise BusinessRuleViolation(
                "The band manager doesn't play, so they can't be invited to a slot.",
                code="manager_cannot_play",
            )
        other_slot = gig.slot_for(member.id)
        if other_slot is not None and other_slot.id != slot.id:
            raise BusinessRuleViolation(
                f"{member.name} is already on this gig for "
                f"{ROLE_LABELS[other_slot.role]}. A member can fill only one slot.",
                code="member_in_two_slots",
            )

        slot.member = member
        slot.status = SlotStatus.INVITED
        slot.pay_cents = data.pay_cents
        slot.responded_at = None
        self._session.commit()
        return self._to_detail(actor, gig)

    def set_slot_pay(
        self, actor: Member, gig_id: int, slot_id: int, pay_cents: int | None
    ) -> GigDetail:
        _require_manager(actor, "set pay")
        gig = self._get_or_404(gig_id)
        slot = _slot_or_404(gig, slot_id)
        slot.pay_cents = pay_cents
        self._session.commit()
        return self._to_detail(actor, gig)

    # ---- Members: answering invitations -----------------------------------------------------

    def accept(self, actor: Member, gig_id: int, slot_id: int) -> GigDetail:
        gig, slot = self._own_pending_invitation(actor, gig_id, slot_id)
        conflict = self._overlapping_gig(actor.id, gig)
        if conflict is not None:
            raise BusinessRuleViolation(
                "You've already accepted another gig at the same time "
                f"({conflict.venue_name or 'untitled gig'}).",
                code="overlapping_gig",
            )
        slot.status = SlotStatus.ACCEPTED
        slot.responded_at = datetime.now(UTC)
        self._session.commit()
        return self._to_detail(actor, gig)

    def decline(self, actor: Member, gig_id: int, slot_id: int) -> GigDetail:
        gig, slot = self._own_pending_invitation(actor, gig_id, slot_id)
        slot.status = SlotStatus.DECLINED
        slot.responded_at = datetime.now(UTC)
        self._session.commit()
        return self._to_detail(actor, gig)

    # ---- Helpers ---------------------------------------------------------------------------

    def _in_transaction[T](self, work: Callable[[], T]) -> T:
        """Run `work`, discarding every change it made if a business rule refuses it."""
        try:
            result = work()
        except AppError:
            self._session.rollback()
            raise
        self._session.commit()
        return result

    def _apply_update(self, actor: Member, gig: Gig, data: GigUpdate) -> GigDetail:
        fields = data.model_fields_set
        if "first_set_at" in fields:
            gig.first_set_at = data.first_set_at
        if "load_in_offset_minutes" in fields:
            gig.load_in_offset_minutes = _or_default(
                data.load_in_offset_minutes, DEFAULT_LOAD_IN_OFFSET_MINUTES
            )
        if "soundcheck_offset_minutes" in fields:
            gig.soundcheck_offset_minutes = _or_default(
                data.soundcheck_offset_minutes, DEFAULT_SOUNDCHECK_OFFSET_MINUTES
            )
        if "performance_minutes" in fields:
            gig.performance_minutes = _or_default(
                data.performance_minutes, DEFAULT_PERFORMANCE_MINUTES
            )
        if "venue_name" in fields:
            gig.venue_name = data.venue_name
        if "venue_address" in fields:
            gig.venue_address = data.venue_address
        if "pay_cents" in fields:
            gig.pay_cents = data.pay_cents
        if "roles" in fields:
            self._replace_roles(gig, data.roles or [])
        if "contacts" in fields:
            self._replace_contacts(gig, data.contacts or [])

        times_changed = fields & {
            "first_set_at",
            "soundcheck_offset_minutes",
            "performance_minutes",
        }
        if times_changed:
            self._require_no_member_overlaps(gig)
        if gig.status is GigStatus.BOOKED:
            _require_complete(gig, "This gig is booked, so it can't be left without:")
        return self._to_detail(actor, gig)

    def _replace_roles(self, gig: Gig, roles: list[Role]) -> None:
        """Keep slots (and their invitations) for roles that stay; add and remove the rest."""
        wanted = set(roles)
        for slot in [slot for slot in gig.slots if slot.role not in wanted]:
            gig.slots.remove(slot)
        existing = {slot.role for slot in gig.slots}
        for role in roles:
            if role not in existing:
                gig.slots.append(GigSlot(role=role, status=SlotStatus.OPEN))
        self._session.flush()

    def _replace_contacts(self, gig: Gig, contacts: list[ContactIn]) -> None:
        gig.contacts.clear()
        self._session.flush()
        gig.contacts.extend(_contact(contact) for contact in contacts)
        self._session.flush()

    def _require_no_member_overlaps(self, gig: Gig) -> None:
        for slot in gig.slots:
            if slot.status is SlotStatus.ACCEPTED and slot.member is not None:
                conflict = self._overlapping_gig(slot.member.id, gig)
                if conflict is not None:
                    raise BusinessRuleViolation(
                        f"{slot.member.name} has already accepted another gig at the new time "
                        f"({conflict.venue_name or 'untitled gig'}).",
                        code="overlapping_gig",
                    )

    def _overlapping_gig(self, member_id: int, gig: Gig) -> Gig | None:
        """Another gig the member accepted whose busy time (soundcheck to end) overlaps this one."""
        window = _busy_window(gig)
        if window is None:
            return None
        start, end = window
        for other in self._gigs.accepted_by_member(member_id, exclude_gig_id=gig.id):
            other_window = _busy_window(other)
            if other_window is not None and start < other_window[1] and other_window[0] < end:
                return other
        return None

    def _own_pending_invitation(
        self, actor: Member, gig_id: int, slot_id: int
    ) -> tuple[Gig, GigSlot]:
        gig = self._get_or_404(gig_id)
        own_slot = gig.slot_for(actor.id)
        if own_slot is None:
            # Same answer as a missing gig, so members can't probe for other gigs.
            raise _gig_not_found()
        slot = _slot_or_404(gig, slot_id)
        if slot.id != own_slot.id:
            raise PermissionDeniedError(
                "That invitation is for someone else.", code="not_your_invitation"
            )
        _require_potential(gig)
        if slot.status is not SlotStatus.INVITED:
            raise BusinessRuleViolation(
                f"You've already answered this invitation ({slot.status.value}).",
                code="invitation_not_pending",
            )
        return gig, slot

    def _require_can_view(self, actor: Member, gig: Gig) -> None:
        if actor.is_manager:
            return
        slot = gig.slot_for(actor.id)
        if gig.status is GigStatus.POTENTIAL:
            if slot is None or slot.status not in SLOT_STATUSES_THAT_SHOW_A_GIG:
                # Same answer as a missing gig, so members can't tell drafts exist.
                raise _gig_not_found()
            return
        if gig.status is not GigStatus.BOOKED:
            raise _gig_not_found()
        if slot is None or slot.status is not SlotStatus.ACCEPTED:
            raise PermissionDeniedError(
                "You're not in the lineup for this gig.", code="not_assigned_to_gig"
            )

    def _get_or_404(self, gig_id: int) -> Gig:
        gig = self._gigs.get(gig_id)
        if gig is None:
            raise _gig_not_found()
        return gig

    def _to_list_item(self, actor: Member, gig: Gig) -> GigListItem:
        slot = None if actor.is_manager else gig.slot_for(actor.id)
        restricted = not actor.is_manager and (
            slot is None or slot.status not in SLOT_STATUSES_THAT_SHOW_A_GIG
        )
        return GigListItem(
            id=gig.id,
            status=gig.status,
            first_set_at=gig.first_set_at,
            venue_name=None if restricted else gig.venue_name,
            lineup_size=None if restricted else lineup_size(len(gig.slots)),
            restricted=restricted,
            my_slot_status=None if restricted or slot is None else slot.status,
        )

    def _to_detail(self, actor: Member, gig: Gig) -> GigDetail:
        own_slot = None if actor.is_manager else gig.slot_for(actor.id)
        ordered = sorted(gig.slots, key=lambda slot: ROLE_ORDER.index(slot.role))
        return GigDetail(
            id=gig.id,
            status=gig.status,
            first_set_at=gig.first_set_at,
            load_in_at=gig.load_in_at,
            soundcheck_at=gig.soundcheck_at,
            end_at=gig.end_at,
            load_in_offset_minutes=gig.load_in_offset_minutes,
            soundcheck_offset_minutes=gig.soundcheck_offset_minutes,
            performance_minutes=gig.performance_minutes,
            venue_name=gig.venue_name,
            venue_address=gig.venue_address,
            lineup_size=lineup_size(len(gig.slots)),
            # Only the manager sees the gig total. Members see only their own slot's pay.
            pay_cents=gig.pay_cents if actor.is_manager else None,
            slots=[
                SlotOut(
                    id=slot.id,
                    role=slot.role,
                    status=slot.status,
                    member=MemberSummary.model_validate(slot.member) if slot.member else None,
                    pay_cents=(slot.pay_cents if actor.is_manager or slot is own_slot else None),
                    responded_at=slot.responded_at,
                )
                for slot in ordered
            ],
            contacts=[
                ContactOut(
                    id=contact.id,
                    label=contact.label,
                    name=contact.name,
                    phone=contact.phone,
                    email=contact.email,
                    notes=contact.notes,
                )
                for contact in gig.contacts
            ],
            my_slot_id=own_slot.id if own_slot else None,
            missing_for_booking=missing_for_booking(gig) if actor.is_manager else [],
            created_at=gig.created_at,
        )


def _require_manager(actor: Member, action: str) -> None:
    if not actor.is_manager:
        raise PermissionDeniedError(f"Only the band manager can {action}.", code="manager_only")


def _require_potential(gig: Gig) -> None:
    if gig.status is not GigStatus.POTENTIAL:
        raise BusinessRuleViolation(
            f"This can only be done while the gig is potential. It is {gig.status.value}.",
            code="gig_not_potential",
        )


def _require_complete(gig: Gig, message_prefix: str) -> None:
    missing = missing_for_booking(gig)
    if missing:
        raise BusinessRuleViolation(
            f"{message_prefix} {', '.join(missing)}.", code="gig_incomplete"
        )


def _busy_window(gig: Gig) -> tuple[datetime, datetime] | None:
    """When a member on this gig is busy: from soundcheck to the end.

    Load-in doesn't count. The product owner's rule is that a member must be able to arrive
    by soundcheck at the latest.
    """
    if gig.soundcheck_at is None or gig.end_at is None:
        return None
    return gig.soundcheck_at, gig.end_at


def _slot_or_404(gig: Gig, slot_id: int) -> GigSlot:
    slot = next((slot for slot in gig.slots if slot.id == slot_id), None)
    if slot is None:
        raise NotFoundError("That slot isn't part of this gig.", code="slot_not_found")
    return slot


def _member_name(slot: GigSlot) -> str:
    return slot.member.name if slot.member else "A member"


def _or_default(value: int | None, default: int) -> int:
    return default if value is None else value


def _gig_not_found() -> NotFoundError:
    return NotFoundError("That gig doesn't exist.", code="gig_not_found")


def _contact(contact: ContactIn) -> GigContact:
    return GigContact(
        label=contact.label,
        name=contact.name,
        phone=contact.phone,
        email=contact.email,
        notes=contact.notes,
    )

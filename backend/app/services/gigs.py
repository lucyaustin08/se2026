"""Business rules for gigs: who can see and change them, and when they can be booked."""

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.errors import AppError, BusinessRuleViolation, NotFoundError, PermissionDeniedError
from app.models.enums import GigStatus, Role
from app.models.gig import (
    DEFAULT_LOAD_IN_OFFSET_MINUTES,
    DEFAULT_SOUNDCHECK_OFFSET_MINUTES,
    Gig,
    GigAssignment,
)
from app.models.member import Member
from app.repositories.gigs import GigRepository
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
    LineupAssignmentIn,
    LineupSlotOut,
)
from app.schemas.members import MemberSummary
from app.services.booking import missing_for_booking
from app.services.lineup import slots_for

# Members only ever see booked gigs. Potential gigs are the manager's working list.
MEMBER_VISIBLE_STATUSES = frozenset({GigStatus.BOOKED})


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
        if actor.is_manager:
            statuses: frozenset[GigStatus] | None = None if status is None else frozenset({status})
            assigned_member_id = None
        else:
            if status is not None and status not in MEMBER_VISIBLE_STATUSES:
                return GigPage(items=[], total=0, page=page, page_size=page_size)
            statuses = MEMBER_VISIBLE_STATUSES
            # Searching matches on venue and contact names, so a member's search only covers
            # gigs they're on. Otherwise a match would reveal details of a restricted gig.
            assigned_member_id = actor.id if q else None

        gigs, total = self._gigs.search(
            q=q,
            statuses=statuses,
            has_date=has_date,
            assigned_member_id=assigned_member_id,
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
        if not actor.is_manager:
            if gig.status not in MEMBER_VISIBLE_STATUSES:
                # Same answer as a missing gig, so members can't tell potential gigs exist.
                raise _gig_not_found()
            if not gig.is_assigned(actor.id):
                raise PermissionDeniedError(
                    "You're not assigned to this gig.", code="not_assigned_to_gig"
                )
        return self._to_detail(actor, gig)

    # ---- Changing --------------------------------------------------------------------------

    def create_gig(self, actor: Member, data: GigCreate) -> GigDetail:
        _require_manager(actor, "add gigs")
        gig = Gig(
            status=GigStatus.POTENTIAL,
            first_set_at=data.first_set_at,
            load_in_offset_minutes=data.load_in_offset_minutes,
            soundcheck_offset_minutes=data.soundcheck_offset_minutes,
            venue_name=data.venue_name,
            venue_address=data.venue_address,
            gig_type=data.gig_type,
            pay_cents=data.pay_cents,
        )
        _set_venue_contact(gig, data.venue_contact)
        _set_booking_contact(gig, data.booking_contact)
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
        if gig.status is not GigStatus.POTENTIAL:
            raise BusinessRuleViolation(
                f"Only potential gigs can be booked. This gig is already {gig.status.value}.",
                code="gig_not_potential",
            )
        _require_complete(gig, "This gig can't be booked until it has:")
        gig.status = GigStatus.BOOKED
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
            gig.load_in_offset_minutes = (
                data.load_in_offset_minutes
                if data.load_in_offset_minutes is not None
                else DEFAULT_LOAD_IN_OFFSET_MINUTES
            )
        if "soundcheck_offset_minutes" in fields:
            gig.soundcheck_offset_minutes = (
                data.soundcheck_offset_minutes
                if data.soundcheck_offset_minutes is not None
                else DEFAULT_SOUNDCHECK_OFFSET_MINUTES
            )
        if "venue_name" in fields:
            gig.venue_name = data.venue_name
        if "venue_address" in fields:
            gig.venue_address = data.venue_address
        if "gig_type" in fields:
            gig.gig_type = data.gig_type
        if "pay_cents" in fields:
            gig.pay_cents = data.pay_cents
        if "venue_contact" in fields:
            _set_venue_contact(gig, data.venue_contact)
        if "booking_contact" in fields:
            _set_booking_contact(gig, data.booking_contact)

        if "lineup" in fields:
            self._replace_lineup(gig, data.lineup or [])
        else:
            _require_lineup_fits_type(gig)

        if gig.status is GigStatus.BOOKED:
            _require_complete(gig, "This gig is booked, so it can't be left without:")
        return self._to_detail(actor, gig)

    def _replace_lineup(self, gig: Gig, entries: list[LineupAssignmentIn]) -> None:
        allowed_slots = slots_for(gig.gig_type)
        if entries and gig.gig_type is None:
            raise BusinessRuleViolation(
                "Choose a gig type before assigning members.", code="gig_type_required"
            )

        seen_slots: set[Role] = set()
        seen_members: set[int] = set()
        for entry in entries:
            if entry.slot not in allowed_slots:
                raise BusinessRuleViolation(
                    f"A {_label(gig.gig_type)} gig has no {_label(entry.slot)} slot.",
                    code="slot_not_in_lineup",
                )
            if entry.slot in seen_slots:
                raise BusinessRuleViolation(
                    f"The {_label(entry.slot)} slot was given more than one member.",
                    code="duplicate_slot",
                )
            if entry.member_id in seen_members:
                raise BusinessRuleViolation(
                    "A member can fill only one slot in a gig's lineup.",
                    code="member_in_two_slots",
                )
            member = self._members.get(entry.member_id)
            if member is None:
                raise BusinessRuleViolation(
                    f"There is no member with id {entry.member_id}.", code="unknown_member"
                )
            if member.primary_role != entry.slot:
                raise BusinessRuleViolation(
                    f"{member.name} can't fill the {_label(entry.slot)} slot because "
                    "it isn't their primary role.",
                    code="member_role_mismatch",
                )
            seen_slots.add(entry.slot)
            seen_members.add(entry.member_id)

        # Delete the old rows before inserting new ones, so reassigning a slot doesn't
        # collide with the one-member-per-slot unique constraint.
        gig.assignments.clear()
        self._session.flush()
        for entry in entries:
            gig.assignments.append(GigAssignment(slot=entry.slot, member_id=entry.member_id))
        self._session.flush()

    def _get_or_404(self, gig_id: int) -> Gig:
        gig = self._gigs.get(gig_id)
        if gig is None:
            raise _gig_not_found()
        return gig

    def _to_list_item(self, actor: Member, gig: Gig) -> GigListItem:
        restricted = not actor.is_manager and not gig.is_assigned(actor.id)
        return GigListItem(
            id=gig.id,
            status=gig.status,
            first_set_at=gig.first_set_at,
            venue_name=None if restricted else gig.venue_name,
            gig_type=None if restricted else gig.gig_type,
            restricted=restricted,
        )

    def _to_detail(self, actor: Member, gig: Gig) -> GigDetail:
        assigned = {assignment.slot: assignment.member for assignment in gig.assignments}
        return GigDetail(
            id=gig.id,
            status=gig.status,
            first_set_at=gig.first_set_at,
            load_in_at=gig.load_in_at,
            soundcheck_at=gig.soundcheck_at,
            load_in_offset_minutes=gig.load_in_offset_minutes,
            soundcheck_offset_minutes=gig.soundcheck_offset_minutes,
            venue_name=gig.venue_name,
            venue_address=gig.venue_address,
            gig_type=gig.gig_type,
            # Whether members see pay is an open product-owner question, so it stays hidden.
            pay_cents=gig.pay_cents if actor.is_manager else None,
            venue_contact=_contact_out(
                gig.venue_contact_name, gig.venue_contact_phone, gig.venue_contact_email
            ),
            booking_contact=_contact_out(
                gig.booking_contact_name, gig.booking_contact_phone, gig.booking_contact_email
            ),
            lineup=[
                LineupSlotOut(
                    slot=slot,
                    member=(
                        MemberSummary.model_validate(assigned[slot]) if slot in assigned else None
                    ),
                )
                for slot in slots_for(gig.gig_type)
            ],
            missing_for_booking=missing_for_booking(gig) if actor.is_manager else [],
            created_at=gig.created_at,
        )


def _require_manager(actor: Member, action: str) -> None:
    if not actor.is_manager:
        raise PermissionDeniedError(f"Only the band manager can {action}.", code="manager_only")


def _require_complete(gig: Gig, message_prefix: str) -> None:
    missing = missing_for_booking(gig)
    if missing:
        raise BusinessRuleViolation(
            f"{message_prefix} {', '.join(missing)}.", code="gig_incomplete"
        )


def _require_lineup_fits_type(gig: Gig) -> None:
    allowed_slots = slots_for(gig.gig_type)
    if any(assignment.slot not in allowed_slots for assignment in gig.assignments):
        raise BusinessRuleViolation(
            "Some assigned members have slots this gig type doesn't include. "
            "Send the new lineup together with the gig type change.",
            code="lineup_not_in_gig_type",
        )


def _gig_not_found() -> NotFoundError:
    return NotFoundError("That gig doesn't exist.", code="gig_not_found")


def _label(value: object) -> str:
    return str(value).replace("_", " ")


def _contact_out(name: str | None, phone: str | None, email: str | None) -> ContactOut | None:
    if name is None and phone is None and email is None:
        return None
    return ContactOut(name=name, phone=phone, email=email)


def _set_venue_contact(gig: Gig, contact: ContactIn | None) -> None:
    gig.venue_contact_name = contact.name if contact else None
    gig.venue_contact_phone = contact.phone if contact else None
    gig.venue_contact_email = contact.email if contact else None


def _set_booking_contact(gig: Gig, contact: ContactIn | None) -> None:
    gig.booking_contact_name = contact.name if contact else None
    gig.booking_contact_phone = contact.phone if contact else None
    gig.booking_contact_email = contact.email if contact else None

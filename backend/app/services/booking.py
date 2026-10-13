"""What a gig needs before the manager can book it."""

from app.models.enums import SlotStatus
from app.models.gig import Gig
from app.services.lineup import ROLE_LABELS, ROLE_ORDER


def missing_for_booking(gig: Gig) -> list[str]:
    """Plain-language names of whatever is still missing. Empty means the gig can be booked."""
    missing: list[str] = []
    if gig.first_set_at is None:
        missing.append("first set date and time")
    if not gig.venue_name:
        missing.append("venue name")
    if not gig.venue_address:
        missing.append("venue address")
    if gig.pay_cents is None:
        missing.append("pay")
    if not any(contact.name and (contact.phone or contact.email) for contact in gig.contacts):
        missing.append("a contact with a name and a phone number or email")

    if not gig.slots:
        missing.append("at least one role in the lineup")
    for slot in sorted(gig.slots, key=lambda s: ROLE_ORDER.index(s.role)):
        if slot.status is not SlotStatus.ACCEPTED:
            missing.append(f"an accepted member for {ROLE_LABELS[slot.role]}")
    leader_accepted = any(
        slot.status is SlotStatus.ACCEPTED
        and slot.member is not None
        and slot.member.is_band_leader
        for slot in gig.slots
    )
    if not leader_accepted:
        missing.append("the band leader, accepted into the lineup")
    return missing

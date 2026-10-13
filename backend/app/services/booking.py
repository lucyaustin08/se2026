"""What a gig needs before the manager can book it."""

from app.models.gig import Gig


def _has_reachable_contact(name: str | None, phone: str | None, email: str | None) -> bool:
    return bool(name) and bool(phone or email)


def missing_for_booking(gig: Gig) -> list[str]:
    """Plain-language names of whatever is still missing. Empty means the gig can be booked."""
    missing: list[str] = []
    if gig.first_set_at is None:
        missing.append("first set date and time")
    if not gig.venue_name:
        missing.append("venue name")
    if not gig.venue_address:
        missing.append("venue address")
    if gig.gig_type is None:
        missing.append("gig type")
    if gig.pay_cents is None:
        missing.append("pay")
    has_contact = _has_reachable_contact(
        gig.venue_contact_name, gig.venue_contact_phone, gig.venue_contact_email
    ) or _has_reachable_contact(
        gig.booking_contact_name, gig.booking_contact_phone, gig.booking_contact_email
    )
    if not has_contact:
        missing.append("a contact with a name and a phone number or email")
    return missing

"""Sample band data for development and demos.

Run with `python -m app.seed`. It does nothing unless SEED_SAMPLE_DATA is true, and it never
touches a database that already has members. Every name, phone number and email is made up.
"""

import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import create_db_engine, create_session_factory
from app.models.enums import GigStatus, GigType, Role
from app.models.gig import Gig, GigAssignment
from app.models.member import Member
from app.repositories.members import MemberRepository

TRUE_VALUES = {"1", "true", "yes", "on"}


def seed_sample_band(session: Session) -> bool:
    """Add the sample band and a few gigs. Returns False if members already exist."""
    if MemberRepository(session).count() > 0:
        return False

    manager = Member(name="Jordan Avery", email="jordan@example.com", is_manager=True)
    sam = Member(name="Sam Rivera", email="sam@example.com", primary_role=Role.RHYTHM_GUITAR_VOCALS)
    casey = Member(name="Casey Morgan", email="casey@example.com", primary_role=Role.LEAD_GUITAR)
    riley = Member(name="Riley Chen", email="riley@example.com", primary_role=Role.BASS)
    taylor = Member(name="Taylor Brooks", email="taylor@example.com", primary_role=Role.DRUMS)
    jamie = Member(name="Jamie Ortiz", email="jamie@example.com", primary_role=Role.SPECIALTY)
    session.add_all([manager, sam, casey, riley, taylor, jamie])
    session.flush()

    # 8:00 PM Eastern on October 18 (EDT) and November 2 (EST), stored in UTC.
    blue_door = Gig(
        status=GigStatus.BOOKED,
        first_set_at=datetime(2026, 10, 19, 0, 0, tzinfo=UTC),
        load_in_offset_minutes=120,
        soundcheck_offset_minutes=75,
        venue_name="The Blue Door",
        venue_address="123 Main St, Spartanburg, SC",
        gig_type=GigType.DUO,
        pay_cents=40_000,
        venue_contact_name="Pat Lee",
        venue_contact_phone="555-0142",
        venue_contact_email="pat@example.com",
    )
    blue_door.assignments = [
        GigAssignment(slot=Role.RHYTHM_GUITAR_VOCALS, member_id=sam.id),
        GigAssignment(slot=Role.LEAD_GUITAR, member_id=casey.id),
    ]
    hub_city = Gig(
        status=GigStatus.POTENTIAL,
        first_set_at=datetime(2026, 11, 3, 1, 0, tzinfo=UTC),
        load_in_offset_minutes=120,
        soundcheck_offset_minutes=60,
        venue_name="Hub City Tap",
        gig_type=GigType.FULL_BAND,
        booking_contact_name="Morgan Hale",
        booking_contact_email="morgan@example.com",
    )
    undated = Gig(
        status=GigStatus.POTENTIAL,
        load_in_offset_minutes=120,
        soundcheck_offset_minutes=60,
        venue_name="Wedding inquiry",
    )
    session.add_all([blue_door, hub_city, undated])
    session.commit()
    return True


def main() -> None:
    if os.environ.get("SEED_SAMPLE_DATA", "").strip().lower() not in TRUE_VALUES:
        print("SEED_SAMPLE_DATA is not set; skipping sample data.")
        return
    engine = create_db_engine(get_settings().database_url)
    try:
        with create_session_factory(engine)() as session:
            added = seed_sample_band(session)
    finally:
        engine.dispose()
    print("Added the sample band." if added else "Members already exist; sample data skipped.")


if __name__ == "__main__":  # pragma: no cover
    main()

"""Enumerations stored in the database and exposed through the API.

Values are lowercase snake_case strings, per the project conventions.
"""

from enum import StrEnum


class GigStatus(StrEnum):
    POTENTIAL = "potential"
    BOOKED = "booked"
    CANCELLED = "cancelled"


class Role(StrEnum):
    """An instrument or role in the band. A member's primary role, and a gig's slot roles."""

    RHYTHM_GUITAR_VOCALS = "rhythm_guitar_vocals"
    LEAD_GUITAR = "lead_guitar"
    BASS = "bass"
    DRUMS = "drums"
    SPECIALTY = "specialty"


class SlotStatus(StrEnum):
    """Where a gig's slot stands: nobody asked yet, asked, said yes, or said no."""

    OPEN = "open"
    INVITED = "invited"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class ContactLabel(StrEnum):
    VENUE = "venue"
    BOOKING = "booking"
    OTHER = "other"


class LineupSize(StrEnum):
    """How big a gig's lineup is. Always computed from its slots, never stored."""

    SOLO = "solo"
    DUO = "duo"
    TRIO = "trio"
    QUARTET = "quartet"
    FULL_BAND = "full_band"

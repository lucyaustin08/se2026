"""Enumerations stored in the database and exposed through the API.

Values are lowercase snake_case strings, per the project conventions.
"""

from enum import StrEnum


class GigStatus(StrEnum):
    POTENTIAL = "potential"
    BOOKED = "booked"
    CANCELLED = "cancelled"


class GigType(StrEnum):
    FULL_BAND = "full_band"
    TRIO = "trio"
    DUO = "duo"


class Role(StrEnum):
    """A member's primary role. Lineup slots use the same values."""

    RHYTHM_GUITAR_VOCALS = "rhythm_guitar_vocals"
    LEAD_GUITAR = "lead_guitar"
    BASS = "bass"
    DRUMS = "drums"
    SPECIALTY = "specialty"

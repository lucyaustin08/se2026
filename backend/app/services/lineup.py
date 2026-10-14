"""Lineup facts derived from a gig's slots."""

from app.models.enums import LineupSize, Role

# The order roles are listed in, wherever a lineup is shown.
ROLE_ORDER: tuple[Role, ...] = (
    Role.RHYTHM_GUITAR_VOCALS,
    Role.LEAD_GUITAR,
    Role.BASS,
    Role.DRUMS,
    Role.SPECIALTY,
)

ROLE_LABELS: dict[Role, str] = {
    Role.RHYTHM_GUITAR_VOCALS: "rhythm guitar/vocals",
    Role.LEAD_GUITAR: "lead guitar",
    Role.BASS: "bass",
    Role.DRUMS: "drums",
    Role.SPECIALTY: "specialty instrument",
}

_SIZES: dict[int, LineupSize] = {
    1: LineupSize.SOLO,
    2: LineupSize.DUO,
    3: LineupSize.TRIO,
    4: LineupSize.QUARTET,
}


def lineup_size(slot_count: int) -> LineupSize | None:
    """Solo, duo, trio or quartet by how many roles the gig needs; five or more is a full band."""
    if slot_count <= 0:
        return None
    return _SIZES.get(slot_count, LineupSize.FULL_BAND)

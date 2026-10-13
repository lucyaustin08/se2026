"""Which lineup slots each gig type has."""

from app.models.enums import GigType, Role

LINEUP_SLOTS: dict[GigType, tuple[Role, ...]] = {
    GigType.DUO: (Role.RHYTHM_GUITAR_VOCALS, Role.LEAD_GUITAR),
    # The trio's third slot is waiting on the product owner (see DECISIONS.md), so only
    # its two fixed slots can be filled for now.
    GigType.TRIO: (Role.RHYTHM_GUITAR_VOCALS, Role.LEAD_GUITAR),
    GigType.FULL_BAND: (
        Role.RHYTHM_GUITAR_VOCALS,
        Role.LEAD_GUITAR,
        Role.BASS,
        Role.DRUMS,
        Role.SPECIALTY,
    ),
}


def slots_for(gig_type: GigType | None) -> tuple[Role, ...]:
    if gig_type is None:
        return ()
    return LINEUP_SLOTS[gig_type]

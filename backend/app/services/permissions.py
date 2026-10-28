"""Who runs the band.

The manager organizes gigs and doesn't play. The band leader plays every gig and decides each
member's pay. They are different people, and both see every gig in full: its total pay,
everyone's pay and the venue contacts. Ordinary members see only what concerns them.
"""

from app.core.errors import PermissionDeniedError
from app.models.member import Member


def runs_the_band(member: Member) -> bool:
    """The manager or the band leader."""
    return member.is_manager or member.is_band_leader


def require_runs_the_band(member: Member, action: str) -> None:
    if not runs_the_band(member):
        raise PermissionDeniedError(
            f"Only the band manager or band leader can {action}.",
            code="manager_or_band_leader_only",
        )

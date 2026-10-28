from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleViolation, NotFoundError, PermissionDeniedError
from app.models.member import Member
from app.repositories.members import MemberRepository
from app.schemas.members import (
    MemberPage,
    MemberProfile,
    MemberProfileUpdate,
    MemberRead,
    MemberSort,
)
from app.services.permissions import runs_the_band


class MemberService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._members = MemberRepository(session)

    def get_actor(self, member_id: int | None) -> Member:
        """Resolve who is acting on this request (the user picker's choice)."""
        if member_id is None:
            raise PermissionDeniedError(
                "Choose who you are before using the app.", code="acting_member_required"
            )
        member = self._members.get(member_id)
        if member is None:
            raise PermissionDeniedError(
                "The chosen member doesn't exist. Choose who you are again.",
                code="unknown_acting_member",
            )
        return member

    def list_members(
        self, *, q: str | None, sort: MemberSort, page: int, page_size: int
    ) -> MemberPage:
        members, total = self._members.search(q=q, sort=sort, page=page, page_size=page_size)
        return MemberPage(
            items=[MemberRead.model_validate(member) for member in members],
            total=total,
            page=page,
            page_size=page_size,
        )

    # ---- Profiles --------------------------------------------------------------------------

    def get_profile(self, actor: Member, member_id: int) -> MemberProfile:
        return _profile(actor, self._get_or_404(member_id))

    def update_profile(
        self, actor: Member, member_id: int, data: MemberProfileUpdate
    ) -> MemberProfile:
        member = self._get_or_404(member_id)
        if actor.id != member.id:
            raise PermissionDeniedError(
                "You can only edit your own profile.", code="not_your_profile"
            )
        fields = data.model_fields_set

        primary = data.primary_role if "primary_role" in fields else member.primary_role
        secondary = data.secondary_role if "secondary_role" in fields else member.secondary_role
        if secondary is not None and secondary == primary:
            raise BusinessRuleViolation(
                "Your secondary instrument has to be different from your primary one.",
                code="secondary_same_as_primary",
            )
        if "email" in fields and data.email is not None:
            owner = self._members.get_by_email(data.email)
            if owner is not None and owner.id != member.id:
                raise BusinessRuleViolation(
                    "Another member already uses that email address.", code="email_taken"
                )

        for field in fields:
            setattr(member, field, getattr(data, field))
        self._session.commit()
        return _profile(actor, member)

    def _get_or_404(self, member_id: int) -> Member:
        member = self._members.get(member_id)
        if member is None:
            raise NotFoundError("That member doesn't exist.", code="member_not_found")
        return member


def _profile(actor: Member, member: Member) -> MemberProfile:
    # Phone and email are private to the member, the manager and the band leader.
    sees_contact = actor.id == member.id or runs_the_band(actor)
    return MemberProfile(
        id=member.id,
        name=member.name,
        email=member.email if sees_contact else None,
        phone=member.phone if sees_contact else None,
        primary_role=member.primary_role,
        secondary_role=member.secondary_role,
        is_manager=member.is_manager,
        is_band_leader=member.is_band_leader,
    )

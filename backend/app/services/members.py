from sqlalchemy.orm import Session

from app.core.errors import PermissionDeniedError
from app.models.member import Member
from app.repositories.members import MemberRepository
from app.schemas.members import MemberPage, MemberRead, MemberSort


class MemberService:
    def __init__(self, session: Session) -> None:
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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.member import Member
from app.schemas.members import MemberSort

_ORDER_BY = {
    MemberSort.NAME: (Member.name.asc(),),
    MemberSort.NAME_DESC: (Member.name.desc(),),
}


class MemberRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, member_id: int) -> Member | None:
        return self._session.get(Member, member_id)

    def search(
        self, *, q: str | None, sort: MemberSort, page: int, page_size: int
    ) -> tuple[list[Member], int]:
        stmt = select(Member)
        if q:
            stmt = stmt.where(Member.name.icontains(q, autoescape=True))

        total = self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(*_ORDER_BY[sort], Member.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return list(self._session.scalars(stmt)), total

    def count(self) -> int:
        return self._session.scalar(select(func.count()).select_from(Member)) or 0

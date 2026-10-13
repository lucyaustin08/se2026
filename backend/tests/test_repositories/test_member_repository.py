from sqlalchemy.orm import Session

from app.repositories.members import MemberRepository
from app.schemas.members import MemberSort
from app.schemas.pagination import MAX_PAGE_SIZE
from tests.factories import Factory


def test_sorts_by_name_both_ways(db: Session, make: Factory) -> None:
    make.member(name="Riley Chen")
    make.member(name="Casey Morgan")
    repo = MemberRepository(db)

    ascending, _ = repo.search(q=None, sort=MemberSort.NAME, page=1, page_size=25)
    descending, _ = repo.search(q=None, sort=MemberSort.NAME_DESC, page=1, page_size=25)

    assert [m.name for m in ascending] == ["Casey Morgan", "Riley Chen"]
    assert [m.name for m in descending] == ["Riley Chen", "Casey Morgan"]


def test_search_by_name_is_case_insensitive(db: Session, make: Factory) -> None:
    make.member(name="Riley Chen")
    make.member(name="Casey Morgan")

    members, total = MemberRepository(db).search(
        q="riley", sort=MemberSort.NAME, page=1, page_size=25
    )

    assert ([m.name for m in members], total) == (["Riley Chen"], 1)


def test_pagination_boundaries(db: Session, make: Factory) -> None:
    for i in range(3):
        make.member(name=f"Member {i}")
    repo = MemberRepository(db)

    def names(page: int, page_size: int) -> tuple[list[str], int]:
        members, total = repo.search(q=None, sort=MemberSort.NAME, page=page, page_size=page_size)
        return [m.name for m in members], total

    assert names(1, 1) == (["Member 0"], 3)
    assert names(2, 2) == (["Member 2"], 3)
    assert names(3, 2) == ([], 3)
    assert names(1, MAX_PAGE_SIZE) == (["Member 0", "Member 1", "Member 2"], 3)


def test_count(db: Session, make: Factory) -> None:
    assert MemberRepository(db).count() == 0
    make.member()
    make.manager()
    assert MemberRepository(db).count() == 2

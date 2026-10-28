from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.repositories.practices import PracticeRepository
from app.schemas.pagination import MAX_PAGE_SIZE
from app.schemas.practices import PracticeSort
from tests.factories import Factory

START = datetime(2026, 10, 22, 22, 0, tzinfo=UTC)


def search(repo: PracticeRepository, **overrides: object) -> tuple[list[int], int]:
    params: dict[str, object] = {
        "q": None,
        "invited_member_id": None,
        "starts_after": None,
        "starts_before": None,
        "sort": PracticeSort.STARTS_AT,
        "page": 1,
        "page_size": 25,
    }
    params.update(overrides)
    items, total = repo.search(**params)  # type: ignore[arg-type]
    return [item.id for item in items], total


def three_practices(make: Factory) -> list[int]:
    riley = make.member()
    return [make.practice(START + timedelta(days=day), [riley]).id for day in (2, 0, 1)]


def test_sorts_by_start_both_ways(db: Session, make: Factory) -> None:
    later, first, middle = three_practices(make)
    repo = PracticeRepository(db)

    assert search(repo)[0] == [first, middle, later]
    assert search(repo, sort=PracticeSort.STARTS_AT_DESC)[0] == [later, middle, first]


def test_pagination_boundaries(db: Session, make: Factory) -> None:
    later, first, middle = three_practices(make)
    repo = PracticeRepository(db)

    assert search(repo, page=1, page_size=1) == ([first], 3)
    assert search(repo, page=3, page_size=1) == ([later], 3)
    assert search(repo, page=4, page_size=1) == ([], 3)
    assert search(repo, page_size=MAX_PAGE_SIZE) == ([first, middle, later], 3)


def test_filters_by_invitee_and_start(db: Session, make: Factory) -> None:
    riley = make.member()
    mine = make.practice(START, [riley])
    make.practice(START, [make.member()])
    later = make.practice(START + timedelta(days=5), [riley])
    repo = PracticeRepository(db)

    assert search(repo, invited_member_id=riley.id)[0] == [mine.id, later.id]
    assert search(repo, invited_member_id=riley.id, starts_after=START + timedelta(days=1))[0] == [
        later.id
    ]
    assert search(repo, invited_member_id=riley.id, starts_before=START + timedelta(days=1))[0] == [
        mine.id
    ]

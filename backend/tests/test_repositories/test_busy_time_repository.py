from datetime import timedelta

from sqlalchemy.orm import Session

from app.repositories.availability import BusyTimeRepository
from app.schemas.availability import BusyTimeSort
from app.schemas.pagination import MAX_PAGE_SIZE
from tests.factories import BLUE_DOOR_FIRST_SET, Factory

START = BLUE_DOOR_FIRST_SET


def search(repo: BusyTimeRepository, **overrides: object) -> tuple[list[int], int]:
    params: dict[str, object] = {
        "member_id": None,
        "ends_after": None,
        "starts_before": None,
        "sort": BusyTimeSort.STARTS_AT,
        "page": 1,
        "page_size": 25,
    }
    params.update(overrides)
    items, total = repo.search(**params)  # type: ignore[arg-type]
    return [item.id for item in items], total


def three_busy_times(make: Factory) -> list[int]:
    riley = make.member()
    return [
        make.busy_time(riley, START + timedelta(days=day), START + timedelta(days=day, hours=1)).id
        for day in (2, 0, 1)
    ]


def test_sorts_by_start_both_ways(db: Session, make: Factory) -> None:
    later, first, middle = three_busy_times(make)
    repo = BusyTimeRepository(db)

    assert search(repo)[0] == [first, middle, later]
    assert search(repo, sort=BusyTimeSort.STARTS_AT_DESC)[0] == [later, middle, first]


def test_pagination_boundaries(db: Session, make: Factory) -> None:
    later, first, middle = three_busy_times(make)
    repo = BusyTimeRepository(db)

    assert search(repo, page=1, page_size=1) == ([first], 3)
    assert search(repo, page=3, page_size=1) == ([later], 3)
    assert search(repo, page=4, page_size=1) == ([], 3)
    assert search(repo, page_size=MAX_PAGE_SIZE) == ([first, middle, later], 3)


def test_overlapping_ignores_busy_times_that_only_touch(db: Session, make: Factory) -> None:
    riley = make.member()
    touching = make.busy_time(riley, START - timedelta(hours=1), START)
    inside = make.busy_time(riley, START + timedelta(minutes=30), START + timedelta(hours=1))
    make.busy_time(make.member(), START, START + timedelta(hours=1))

    found = BusyTimeRepository(db).overlapping(riley.id, START, START + timedelta(hours=2))

    assert [b.id for b in found] == [inside.id]
    assert touching.id not in [b.id for b in found]

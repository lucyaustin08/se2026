from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import seed
from app.models import Base, Gig, Member


def test_seeds_a_manager_a_leader_and_a_member_for_every_role(db: Session) -> None:
    assert seed.seed_sample_band(db) is True

    members = db.scalars(select(Member)).all()
    assert sum(m.is_manager for m in members) == 1
    leaders = [m for m in members if m.is_band_leader]
    assert [(m.name, m.is_manager) for m in leaders] == [("Sam Rivera", False)]
    assert {m.primary_role for m in members if not m.is_manager} == {
        "rhythm_guitar_vocals",
        "lead_guitar",
        "bass",
        "drums",
        "specialty",
    }
    assert db.scalar(select(func.count()).select_from(Gig)) == 3


def test_does_nothing_when_members_already_exist(db: Session) -> None:
    seed.seed_sample_band(db)

    assert seed.seed_sample_band(db) is False
    assert db.scalar(select(func.count()).select_from(Member)) == 6


def test_main_skips_unless_enabled(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SEED_SAMPLE_DATA", raising=False)

    seed.main()

    assert "skipping" in capsys.readouterr().out


def test_main_seeds_the_configured_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    url = f"sqlite:///{tmp_path / 'seed.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SEED_SAMPLE_DATA", "true")

    seed.main()
    seed.main()

    out = capsys.readouterr().out
    assert "Added the sample band." in out
    assert "Members already exist" in out
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Member)) == 6
    engine.dispose()

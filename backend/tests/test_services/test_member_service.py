"""Profile rules, tested through the service with a real (in-memory) database."""

import pytest
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleViolation, NotFoundError, PermissionDeniedError
from app.models.enums import Role
from app.models.member import Member
from app.schemas.members import MemberProfileUpdate
from app.services.members import MemberService
from tests.factories import Factory


@pytest.fixture
def service(db: Session) -> MemberService:
    return MemberService(db)


def stored(db: Session, member: Member) -> Member:
    db.expire_all()
    found = db.get(Member, member.id)
    assert found is not None
    return found


# ---- Reading a profile, and who sees contact details ---------------------------------------


def test_a_member_sees_their_own_phone_and_email(service: MemberService, make: Factory) -> None:
    riley = make.member(name="Riley Chen", phone="555-0103")

    profile = service.get_profile(riley, riley.id)

    assert (profile.name, profile.email, profile.phone) == ("Riley Chen", riley.email, "555-0103")


def test_other_members_dont_see_phone_or_email(service: MemberService, make: Factory) -> None:
    riley = make.member(name="Riley Chen", phone="555-0103")

    profile = service.get_profile(make.member(), riley.id)

    assert profile.name == "Riley Chen"
    assert (profile.email, profile.phone) == (None, None)


@pytest.mark.parametrize("who", ["manager", "band leader"])
def test_the_manager_and_band_leader_see_phone_and_email(
    service: MemberService, make: Factory, who: str
) -> None:
    riley = make.member(phone="555-0103")
    reader = make.manager() if who == "manager" else make.leader()

    profile = service.get_profile(reader, riley.id)

    assert (profile.email, profile.phone) == (riley.email, "555-0103")


def test_a_missing_member_is_not_found(service: MemberService, make: Factory) -> None:
    with pytest.raises(NotFoundError) as error:
        service.get_profile(make.member(), 9999)

    assert error.value.code == "member_not_found"


# ---- Editing your own profile ----------------------------------------------------------------


def test_a_member_edits_their_own_profile(
    service: MemberService, make: Factory, db: Session
) -> None:
    riley = make.member(name="Riley Chen", role=Role.BASS)

    profile = service.update_profile(
        riley,
        riley.id,
        MemberProfileUpdate(
            name="Riley Chen-Park",
            email="riley.cp@example.com",
            phone="555-0199",
            secondary_role=Role.DRUMS,
        ),
    )

    assert (profile.name, profile.phone, profile.secondary_role) == (
        "Riley Chen-Park",
        "555-0199",
        Role.DRUMS,
    )
    saved = stored(db, riley)
    assert (saved.email, saved.primary_role) == ("riley.cp@example.com", Role.BASS)


def test_omitted_fields_are_unchanged_and_null_clears_the_phone(
    service: MemberService, make: Factory, db: Session
) -> None:
    riley = make.member(name="Riley Chen", phone="555-0103")

    service.update_profile(riley, riley.id, MemberProfileUpdate(phone=None))

    saved = stored(db, riley)
    assert (saved.name, saved.phone) == ("Riley Chen", None)


@pytest.mark.parametrize("who", ["member", "manager", "band leader"])
def test_nobody_edits_someone_elses_profile(
    service: MemberService, make: Factory, db: Session, who: str
) -> None:
    riley = make.member(name="Riley Chen")
    actor = {"member": make.member, "manager": make.manager, "band leader": make.leader}[who]()

    with pytest.raises(PermissionDeniedError) as error:
        service.update_profile(actor, riley.id, MemberProfileUpdate(name="Changed"))

    assert error.value.code == "not_your_profile"
    assert stored(db, riley).name == "Riley Chen"


def test_the_secondary_instrument_cant_match_the_primary(
    service: MemberService, make: Factory, db: Session
) -> None:
    riley = make.member(role=Role.BASS)

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_profile(riley, riley.id, MemberProfileUpdate(secondary_role=Role.BASS))

    assert error.value.code == "secondary_same_as_primary"
    assert stored(db, riley).secondary_role is None


def test_changing_the_primary_to_match_the_secondary_is_refused(
    service: MemberService, make: Factory, db: Session
) -> None:
    riley = make.member(role=Role.BASS)
    service.update_profile(riley, riley.id, MemberProfileUpdate(secondary_role=Role.DRUMS))

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_profile(riley, riley.id, MemberProfileUpdate(primary_role=Role.DRUMS))

    assert error.value.code == "secondary_same_as_primary"
    assert stored(db, riley).primary_role is Role.BASS


def test_swapping_primary_and_secondary_in_one_edit_is_allowed(
    service: MemberService, make: Factory
) -> None:
    riley = make.member(role=Role.BASS)
    service.update_profile(riley, riley.id, MemberProfileUpdate(secondary_role=Role.DRUMS))

    profile = service.update_profile(
        riley,
        riley.id,
        MemberProfileUpdate(primary_role=Role.DRUMS, secondary_role=Role.BASS),
    )

    assert (profile.primary_role, profile.secondary_role) == (Role.DRUMS, Role.BASS)


def test_an_email_another_member_uses_is_refused(
    service: MemberService, make: Factory, db: Session
) -> None:
    casey = make.member()
    riley = make.member()

    with pytest.raises(BusinessRuleViolation) as error:
        service.update_profile(riley, riley.id, MemberProfileUpdate(email=casey.email.upper()))

    assert error.value.code == "email_taken"
    assert stored(db, riley).email != casey.email


def test_keeping_your_own_email_is_allowed(service: MemberService, make: Factory) -> None:
    riley = make.member()

    profile = service.update_profile(riley, riley.id, MemberProfileUpdate(email=riley.email))

    assert profile.email == riley.email


def test_name_and_email_cant_be_cleared() -> None:
    for field in ("name", "email"):
        with pytest.raises(ValueError, match=f"{field} can't be empty"):
            MemberProfileUpdate.model_validate({field: None})


def test_roles_cant_be_sent_at_all() -> None:
    for field in ("is_manager", "is_band_leader"):
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            MemberProfileUpdate.model_validate({field: True})

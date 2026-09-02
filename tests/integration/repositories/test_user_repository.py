"""SQLAlchemy user repository integration tests."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.factories import make_user

async def test_create_and_get_by_id(user_repository: SQLAlchemyUserRepository, db_session):
    user = make_user(email="create-get@example.test")
    created = await user_repository.create(user)
    await db_session.commit()

    loaded = await user_repository.get_by_id(created.id)
    assert loaded is not None
    assert loaded.email == "create-get@example.test"
    assert loaded.first_name == user.first_name


async def test_get_by_email_is_case_insensitive(
    user_repository: SQLAlchemyUserRepository,
    db_session,
):
    await user_repository.create(make_user(email="CaseSensitive@Example.test"))
    await db_session.commit()

    loaded = await user_repository.get_by_email("casesensitive@example.test")
    assert loaded is not None
    assert loaded.email == "casesensitive@example.test"


async def test_email_exists(user_repository: SQLAlchemyUserRepository, db_session):
    await user_repository.create(make_user(email="exists@example.test"))
    await db_session.commit()

    assert await user_repository.email_exists("exists@example.test") is True
    assert await user_repository.email_exists("missing@example.test") is False


async def test_update_user(user_repository: SQLAlchemyUserRepository, db_session):
    created = await user_repository.create(make_user(email="update@example.test"))
    await db_session.commit()

    created.first_name = "Updated"
    created.touch()
    updated = await user_repository.update(created)
    await db_session.commit()

    loaded = await user_repository.get_by_id(updated.id)
    assert loaded is not None
    assert loaded.first_name == "Updated"


async def test_delete_user(user_repository: SQLAlchemyUserRepository, db_session):
    created = await user_repository.create(make_user(email="delete@example.test"))
    await db_session.commit()

    deleted = await user_repository.delete(created.id)
    await db_session.commit()

    assert deleted is True
    assert await user_repository.get_by_id(created.id) is None


async def test_increment_token_version(user_repository: SQLAlchemyUserRepository, db_session):
    created = await user_repository.create(make_user(email="token-version@example.test"))
    await db_session.commit()

    updated = await user_repository.increment_token_version(created.id)
    await db_session.commit()

    assert updated.token_version == 1
    loaded = await user_repository.get_by_id(created.id)
    assert loaded is not None
    assert loaded.token_version == 1


async def test_duplicate_email_raises_integrity_error(
    user_repository: SQLAlchemyUserRepository,
    db_session,
):
    email = "dup-user@example.test"
    await user_repository.create(make_user(email=email))
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await user_repository.create(make_user(email=email))
    await db_session.rollback()

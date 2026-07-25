"""Transaction commit, rollback, and session isolation integration tests."""

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.database import truncate_application_tables
from tests.integration.support.factories import make_user


@pytest_asyncio.fixture(autouse=True)
async def clean_application_tables(integration_engine):
    """Ensure transaction tests start from an empty application schema."""
    session_factory = async_sessionmaker(
        bind=integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        await truncate_application_tables(session)
        await session.commit()
    yield


async def test_commit_makes_data_visible_in_new_session(integration_engine):
    """Committed rows are visible from a separate database session."""
    session_factory = async_sessionmaker(
        bind=integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    user = make_user(email="committed-visible@example.test")

    async with session_factory() as writer:
        repo = SQLAlchemyUserRepository(writer)
        created = await repo.create(user)
        await writer.commit()

    async with session_factory() as reader:
        repo = SQLAlchemyUserRepository(reader)
        loaded = await repo.get_by_id(created.id)
        assert loaded is not None
        assert loaded.email == "committed-visible@example.test"


async def test_rollback_discards_uncommitted_changes(integration_engine):
    """Uncommitted rows are not visible after rollback."""
    session_factory = async_sessionmaker(
        bind=integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    user = make_user(email="rolled-back@example.test")

    async with session_factory() as writer:
        repo = SQLAlchemyUserRepository(writer)
        created = await repo.create(user)
        await writer.rollback()

    async with session_factory() as reader:
        repo = SQLAlchemyUserRepository(reader)
        assert await repo.get_by_id(created.id) is None


async def test_session_isolation_before_commit(integration_engine):
    """Another session cannot see uncommitted inserts."""
    session_factory = async_sessionmaker(
        bind=integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    user = make_user(email="uncommitted-isolated@example.test")

    async with session_factory() as writer:
        repo = SQLAlchemyUserRepository(writer)
        created = await repo.create(user)

        async with session_factory() as reader:
            other_repo = SQLAlchemyUserRepository(reader)
            assert await other_repo.get_by_id(created.id) is None

        await writer.rollback()


async def test_unique_email_constraint_on_commit(user_repository, db_session):
    """Duplicate emails raise IntegrityError on commit."""
    email = "duplicate-email@example.test"
    await user_repository.create(make_user(email=email))
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await user_repository.create(make_user(email=email))
    await db_session.rollback()

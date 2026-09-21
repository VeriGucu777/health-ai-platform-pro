"""Fixtures for PostgreSQL integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.repositories.appointment_repository import SQLAlchemyAppointmentRepository
from app.infrastructure.repositories.health_measurement_repository import (
    SQLAlchemyHealthMeasurementRepository,
)
from app.infrastructure.repositories.medical_record_repository import SQLAlchemyMedicalRecordRepository
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.risk_assessment_history_repository import (
    SQLAlchemyRiskAssessmentHistoryRepository,
)
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.database import (
    IntegrationDatabaseUrls,
    build_integration_urls,
    docker_available,
    run_alembic_upgrade,
    truncate_application_tables,
)

INTEGRATION_ROOT = Path(__file__).parent.resolve()


def _require_docker_and_testcontainers():
    if not docker_available():
        pytest.skip("Docker is not available; skipping PostgreSQL integration tests")
    try:
        from testcontainers.postgres import PostgresContainer  # noqa: F401
    except ImportError:
        pytest.skip(
            "testcontainers is not installed; skipping PostgreSQL integration tests",
        )


def pytest_collection_modifyitems(items):
    """Mark every test under tests/integration with the integration marker."""
    for item in items:
        item_path = Path(str(getattr(item, "path", item.fspath))).resolve()
        if INTEGRATION_ROOT in item_path.parents:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def postgres_container():
    """Start an ephemeral PostgreSQL instance for the integration test session."""
    _require_docker_and_testcontainers()
    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer("pgvector/pgvector:pg16")
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def integration_database_urls(postgres_container) -> IntegrationDatabaseUrls:
    """Validated database URLs from the Testcontainers PostgreSQL instance."""
    return build_integration_urls(postgres_container.get_connection_url())


@pytest.fixture(scope="session")
def migrated_database(integration_database_urls: IntegrationDatabaseUrls) -> IntegrationDatabaseUrls:
    """Apply Alembic migrations once per session."""
    run_alembic_upgrade(integration_database_urls.sync_url)
    return integration_database_urls


@pytest_asyncio.fixture
async def integration_engine(migrated_database: IntegrationDatabaseUrls):
    """Async engine bound to the ephemeral integration database."""
    engine = create_async_engine(
        migrated_database.async_url,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(integration_engine):
    """Function-scoped session with truncated tables before and after each test."""
    session_factory = async_sessionmaker(
        bind=integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with session_factory() as session:
        await truncate_application_tables(session)
        await session.commit()
        try:
            yield session
        finally:
            await session.rollback()
            await truncate_application_tables(session)
            await session.commit()


@pytest.fixture
def user_repository(db_session: AsyncSession) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(db_session)


@pytest.fixture
def patient_repository(db_session: AsyncSession) -> SQLAlchemyPatientRepository:
    return SQLAlchemyPatientRepository(db_session)


@pytest.fixture
def appointment_repository(db_session: AsyncSession) -> SQLAlchemyAppointmentRepository:
    return SQLAlchemyAppointmentRepository(db_session)


@pytest.fixture
def medical_record_repository(db_session: AsyncSession) -> SQLAlchemyMedicalRecordRepository:
    return SQLAlchemyMedicalRecordRepository(db_session)


@pytest.fixture
def health_measurement_repository(
    db_session: AsyncSession,
) -> SQLAlchemyHealthMeasurementRepository:
    return SQLAlchemyHealthMeasurementRepository(db_session)


@pytest.fixture
def risk_assessment_history_repository(
    db_session: AsyncSession,
) -> SQLAlchemyRiskAssessmentHistoryRepository:
    return SQLAlchemyRiskAssessmentHistoryRepository(db_session)

"""Database helpers for PostgreSQL integration tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import NullPool

BACKEND_ROOT = Path(__file__).resolve().parents[3]

BLOCKED_DATABASE_NAMES = frozenset({"health_ai_platform"})

EXPECTED_TABLES = frozenset(
    {
        "users",
        "organizations",
        "organization_memberships",
        "patients",
        "patient_assignments",
        "patient_consents",
        "appointments",
        "medical_records",
        "health_measurements",
        "audit_logs",
        "risk_assessment_history",
        "clinical_retrieval_vectors",
        "alembic_version",
    }
)

TRUNCATE_TABLES = (
    "clinical_retrieval_vectors",
    "risk_assessment_history",
    "health_measurements",
    "medical_records",
    "appointments",
    "patient_assignments",
    "patient_consents",
    "patients",
    "organization_memberships",
    "organizations",
    "users",
)


@dataclass(frozen=True)
class IntegrationDatabaseUrls:
    """Async and sync URLs for the ephemeral integration database."""

    sync_url: str
    async_url: str


def docker_available() -> bool:
    """Return True when the Docker daemon responds to a ping."""
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


def database_name_from_url(url: str) -> str:
    """Extract the database name from a SQLAlchemy URL."""
    normalized = (
        url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )
    parsed = urlparse(normalized)
    return parsed.path.lstrip("/")


def assert_safe_integration_url(url: str) -> None:
    """Refuse URLs that match known production database names."""
    db_name = database_name_from_url(url)
    if db_name in BLOCKED_DATABASE_NAMES:
        raise RuntimeError(
            f"Refusing integration tests against blocked database '{db_name}'. "
            "Use an ephemeral Testcontainers database only."
        )


def to_sync_url(url: str) -> str:
    """Convert a PostgreSQL URL to the psycopg sync driver."""
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "+psycopg")
    if "+psycopg2" in url:
        return url.replace("+psycopg2", "+psycopg")
    if "+psycopg" in url:
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def to_async_url(url: str) -> str:
    """Convert a PostgreSQL URL to the asyncpg async driver."""
    if "+asyncpg" in url:
        return url
    if "+psycopg" in url:
        return url.replace("+psycopg", "+asyncpg")
    if "+psycopg2" in url:
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def build_integration_urls(raw_container_url: str) -> IntegrationDatabaseUrls:
    """Build validated sync/async URLs from a Testcontainers connection string."""
    sync_url = to_sync_url(raw_container_url)
    async_url = to_async_url(sync_url)
    assert_safe_integration_url(sync_url)
    assert_safe_integration_url(async_url)
    return IntegrationDatabaseUrls(sync_url=sync_url, async_url=async_url)


def build_alembic_config(sync_url: str) -> Config:
    """Build Alembic config bound to the integration database only."""
    assert_safe_integration_url(sync_url)
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.attributes["integration_database_url"] = sync_url
    return cfg


def run_alembic_upgrade(sync_url: str, revision: str = "head") -> None:
    """Apply Alembic migrations to the integration database."""
    cfg = build_alembic_config(sync_url)
    command.upgrade(cfg, revision)


def run_alembic_downgrade(sync_url: str, revision: str = "base") -> None:
    """Downgrade Alembic migrations on the integration database."""
    cfg = build_alembic_config(sync_url)
    command.downgrade(cfg, revision)


async def truncate_application_tables(session: AsyncSession) -> None:
    """Remove all application rows while preserving schema."""
    table_list = ", ".join(TRUNCATE_TABLES)
    await session.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))


async def list_public_tables(engine: AsyncEngine) -> set[str]:
    """Return table names in the public schema."""
    query = text(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
    )
    async with engine.connect() as connection:
        result = await connection.execute(query)
        return {row[0] for row in result.fetchall()}


def list_public_tables_sync(sync_url: str) -> set[str]:
    """Return public schema table names using a one-off sync connection."""
    assert_safe_integration_url(sync_url)
    query = text(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
    )
    engine = create_engine(sync_url, poolclass=NullPool)
    with engine.connect() as connection:
        result = connection.execute(query)
        return {row[0] for row in result.fetchall()}

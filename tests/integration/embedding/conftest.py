"""Fixtures for ONNX + FastEmbed integration tests (Linux/Docker)."""

from __future__ import annotations

import os
import time
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.infrastructure.database.session import reset_database_engine
from app.main import create_app
from tests.integration.support.database import (
    IntegrationDatabaseUrls,
    build_integration_urls,
    run_alembic_upgrade,
    to_sync_url,
    truncate_application_tables,
)


def _embedding_runtime_required() -> bool:
    return os.environ.get("EMBEDDING_RUNTIME_REQUIRED", "").strip() == "1"


def _onnx_runtime_importable() -> bool:
    try:
        import onnxruntime  # noqa: F401
        import fastembed  # noqa: F401
    except ImportError:
        return False
    return True


def _wait_for_database(raw_url: str, *, attempts: int = 40, delay_seconds: float = 1.0) -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    sync_url = to_sync_url(raw_url)
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            engine = create_engine(sync_url, poolclass=NullPool)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(delay_seconds)
    raise RuntimeError(f"PostgreSQL not ready at {sync_url}: {last_error}")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "tests/integration/embedding" in str(item.fspath):
            item.add_marker(pytest.mark.embedding_runtime)


@pytest.fixture(scope="session", autouse=True)
def require_embedding_runtime_session():
    """In Docker (EMBEDDING_RUNTIME_REQUIRED=1) missing ONNX must fail, not skip."""
    if _embedding_runtime_required() and not _onnx_runtime_importable():
        pytest.fail(
            "EMBEDDING_RUNTIME_REQUIRED=1 but fastembed/onnxruntime could not be imported. "
            "Install production dependencies in the Linux/Docker image.",
        )
    if not _onnx_runtime_importable():
        pytest.skip("ONNX/fastembed runtime unavailable on this host; run docker-compose.embedding-test.yml")


@pytest.fixture(scope="session")
def postgres_container():
    """Compose-managed PostgreSQL — avoid Testcontainers Ryuk in Docker-in-Docker."""
    yield None


@pytest.fixture(scope="session")
def integration_database_urls() -> IntegrationDatabaseUrls:
    raw = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@postgres:5432/health_ai_embedding_e2e",
    )
    _wait_for_database(raw)
    return build_integration_urls(raw)


@pytest.fixture(scope="session")
def migrated_database(integration_database_urls: IntegrationDatabaseUrls) -> IntegrationDatabaseUrls:
    run_alembic_upgrade(integration_database_urls.sync_url)
    return integration_database_urls


@pytest_asyncio.fixture
async def integration_engine(migrated_database: IntegrationDatabaseUrls):
    engine = create_async_engine(
        migrated_database.async_url,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(integration_engine):
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


@pytest.fixture(scope="session", autouse=True)
def _reset_embedding_provider_cache_session():
    from app.infrastructure.embeddings.embedding_factory import reset_embedding_provider_cache

    reset_embedding_provider_cache()
    yield
    reset_embedding_provider_cache()


@pytest.fixture(scope="session")
def production_local_embedding_settings() -> Settings:
    from app.application.clinical_retrieval.constants import DEFAULT_LOCAL_EMBEDDING_MODEL

    return Settings(
        ENVIRONMENT="development",
        DEBUG=True,
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        AUTH_RATE_LIMIT_ENABLED=False,
        HEALTH_CHECK_DB_ENABLED=False,
        METRICS_ENABLED=False,
        EMBEDDING_PROVIDER="local",
        LOCAL_EMBEDDING_MODEL=DEFAULT_LOCAL_EMBEDDING_MODEL,
        EMBEDDING_VERSION="3",
    )


@pytest.fixture(scope="session")
def production_local_embedding_provider(production_local_embedding_settings: Settings):
    """Single ONNX model load for the embedding integration session."""
    from app.infrastructure.embeddings.embedding_factory import get_embedding_provider
    from app.infrastructure.embeddings.local_embedding_provider import LocalEmbeddingProvider

    provider = get_embedding_provider(production_local_embedding_settings)
    assert isinstance(provider, LocalEmbeddingProvider)
    return provider


@pytest_asyncio.fixture
async def pg_live_client(
    migrated_database: IntegrationDatabaseUrls,
    production_local_embedding_settings: Settings,
    db_session,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client against real PostgreSQL + pgvector + local embeddings (no in-memory overrides)."""
    _ = db_session
    get_settings.cache_clear()
    reset_database_engine()
    settings = Settings(
        ENVIRONMENT=production_local_embedding_settings.environment,
        DEBUG=production_local_embedding_settings.debug,
        JWT_SECRET_KEY=production_local_embedding_settings.jwt_secret_key,
        AUTH_RATE_LIMIT_ENABLED=production_local_embedding_settings.auth_rate_limit_enabled,
        HEALTH_CHECK_DB_ENABLED=production_local_embedding_settings.health_check_db_enabled,
        METRICS_ENABLED=production_local_embedding_settings.metrics_enabled,
        EMBEDDING_PROVIDER=production_local_embedding_settings.embedding_provider,
        LOCAL_EMBEDDING_MODEL=production_local_embedding_settings.local_embedding_model,
        EMBEDDING_VERSION=production_local_embedding_settings.embedding_version,
        DATABASE_URL=str(migrated_database.async_url),
    )
    application = create_app(settings)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    get_settings.cache_clear()
    reset_database_engine()

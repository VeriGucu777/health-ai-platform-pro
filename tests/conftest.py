"""Shared pytest fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.api.deps import get_auth_service, get_patient_service
from app.application.services.auth_service import AuthService
from app.application.services.patient_service import PatientService
from app.core.config import Settings, get_settings
from app.infrastructure.database.session import reset_database_engine
from app.main import create_app
from tests.support.memory_patient_repository import InMemoryPatientRepository
from tests.support.memory_user_repository import InMemoryUserRepository


@pytest.fixture
def test_settings() -> Settings:
    """Override settings for test environment."""
    return Settings(
        ENVIRONMENT="development",
        DEBUG=True,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
    )


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    """Fresh in-memory user store for each test."""
    return InMemoryUserRepository()


@pytest.fixture
def patient_repository() -> InMemoryPatientRepository:
    """Fresh in-memory patient store for each test."""
    return InMemoryPatientRepository()


@pytest.fixture
def app(test_settings: Settings):
    """Create a test FastAPI application."""
    get_settings.cache_clear()
    reset_database_engine()
    application = create_app(test_settings)
    yield application
    get_settings.cache_clear()
    reset_database_engine()


@pytest.fixture
async def client(app, user_repository: InMemoryUserRepository, patient_repository: InMemoryPatientRepository):
    """Async HTTP client with in-memory auth and patient backends."""

    def override_auth_service(request: Request) -> AuthService:
        return AuthService(user_repository, request.app.state.settings)

    def override_patient_service(_request: Request) -> PatientService:
        return PatientService(patient_repository)

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_patient_service] = override_patient_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

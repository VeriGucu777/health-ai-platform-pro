"""Shared pytest fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.api.deps import (
    get_appointment_service,
    get_auth_service,
    get_health_measurement_analytics_service,
    get_health_measurement_service,
    get_medical_record_service,
    get_patient_health_report_service,
    get_patient_service,
)
from app.application.services.appointment_service import AppointmentService
from app.application.services.auth_service import AuthService
from app.application.services.health_measurement_analytics_service import (
    HealthMeasurementAnalyticsService,
)
from app.application.services.health_measurement_service import HealthMeasurementService
from app.application.services.medical_record_service import MedicalRecordService
from app.application.services.patient_health_report_service import PatientHealthReportService
from app.application.services.patient_service import PatientService
from app.core.config import Settings, get_settings
from app.infrastructure.database.session import reset_database_engine
from app.main import create_app
from tests.support.memory_appointment_repository import InMemoryAppointmentRepository
from tests.support.memory_health_measurement_repository import InMemoryHealthMeasurementRepository
from tests.support.memory_medical_record_repository import InMemoryMedicalRecordRepository
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
def appointment_repository() -> InMemoryAppointmentRepository:
    """Fresh in-memory appointment store for each test."""
    return InMemoryAppointmentRepository()


@pytest.fixture
def medical_record_repository() -> InMemoryMedicalRecordRepository:
    """Fresh in-memory medical record store for each test."""
    return InMemoryMedicalRecordRepository()


@pytest.fixture
def health_measurement_repository() -> InMemoryHealthMeasurementRepository:
    """Fresh in-memory health measurement store for each test."""
    return InMemoryHealthMeasurementRepository()


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
async def client(
    app,
    user_repository: InMemoryUserRepository,
    patient_repository: InMemoryPatientRepository,
    appointment_repository: InMemoryAppointmentRepository,
    medical_record_repository: InMemoryMedicalRecordRepository,
    health_measurement_repository: InMemoryHealthMeasurementRepository,
):
    """Async HTTP client with in-memory backends for all business modules."""

    def override_auth_service(request: Request) -> AuthService:
        return AuthService(user_repository, request.app.state.settings)

    def override_patient_service(_request: Request) -> PatientService:
        return PatientService(patient_repository)

    def override_appointment_service(_request: Request) -> AppointmentService:
        return AppointmentService(appointment_repository, patient_repository)

    def override_medical_record_service(_request: Request) -> MedicalRecordService:
        return MedicalRecordService(medical_record_repository, patient_repository)

    def override_health_measurement_service(_request: Request) -> HealthMeasurementService:
        return HealthMeasurementService(health_measurement_repository, patient_repository)

    def override_health_measurement_analytics_service(
        _request: Request,
    ) -> HealthMeasurementAnalyticsService:
        return HealthMeasurementAnalyticsService(health_measurement_repository, patient_repository)

    def override_patient_health_report_service(_request: Request) -> PatientHealthReportService:
        return PatientHealthReportService(
            PatientService(patient_repository),
            MedicalRecordService(medical_record_repository, patient_repository),
            HealthMeasurementAnalyticsService(health_measurement_repository, patient_repository),
        )

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_patient_service] = override_patient_service
    app.dependency_overrides[get_appointment_service] = override_appointment_service
    app.dependency_overrides[get_medical_record_service] = override_medical_record_service
    app.dependency_overrides[get_health_measurement_service] = override_health_measurement_service
    app.dependency_overrides[get_health_measurement_analytics_service] = (
        override_health_measurement_analytics_service
    )
    app.dependency_overrides[get_patient_health_report_service] = (
        override_patient_health_report_service
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

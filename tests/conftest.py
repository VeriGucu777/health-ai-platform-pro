"""Shared pytest fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.api.deps import (
    get_appointment_service,
    get_audit_service,
    get_auth_service,
    get_email_verification_service,
    get_clinic_admin_organization_service,
    get_patient_consent_service,
    get_diabetes_risk_assessment_service,
    get_heart_disease_risk_assessment_service,
    get_health_measurement_analytics_service,
    get_health_measurement_service,
    get_medical_record_service,
    get_clinical_narrative_service,
    get_clinical_retrieval_service,
    get_patient_clinical_summary_service,
    get_patient_clinical_timeline_service,
    get_patient_health_report_service,
    get_patient_service,
    get_risk_assessment_history_service,
    get_stroke_risk_assessment_service,
)
from app.application.services.appointment_service import AppointmentService
from app.application.services.audit_service import AuditService
from app.application.services.auth_service import AuthService
from app.application.services.email_verification_service import EmailVerificationService
from app.application.services.clinic_admin_organization_service import (
    ClinicAdminOrganizationService,
)
from app.application.services.patient_consent_service import PatientConsentService
from app.application.services.diabetes_risk_assessment_service import DiabetesRiskAssessmentService
from app.application.services.heart_disease_risk_assessment_service import (
    HeartDiseaseRiskAssessmentService,
)
from app.application.services.health_measurement_analytics_service import (
    HealthMeasurementAnalyticsService,
)
from app.application.services.health_measurement_service import HealthMeasurementService
from app.application.services.medical_record_service import MedicalRecordService
from app.application.services.clinical_narrative_service import ClinicalNarrativeService
from app.application.services.patient_clinical_summary_service import (
    PatientClinicalSummaryService,
)
from app.application.services.patient_clinical_timeline_service import (
    PatientClinicalTimelineService,
)
from app.application.services.patient_health_report_service import PatientHealthReportService
from app.application.services.patient_service import PatientService
from app.application.services.stroke_risk_assessment_service import StrokeRiskAssessmentService
from app.core.config import Settings, get_settings
from app.infrastructure.database.session import reset_database_engine
from app.main import create_app
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository
from tests.support.memory_appointment_repository import InMemoryAppointmentRepository
from tests.support.memory_health_measurement_repository import InMemoryHealthMeasurementRepository
from tests.support.memory_medical_record_repository import InMemoryMedicalRecordRepository
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)
from tests.support.memory_organization_repository import InMemoryOrganizationRepository
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_consent_repository import InMemoryPatientConsentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository
from tests.support.memory_email_verification_token_repository import (
    InMemoryEmailVerificationTokenRepository,
)
from tests.support.memory_user_repository import InMemoryUserRepository
from app.infrastructure.email.recording_email_sender import RecordingEmailSender
from tests.support.clinical_read_service_factory import (
    build_clinical_narrative_service,
    build_clinical_retrieval_service,
    build_clinical_summary_service,
    build_clinical_timeline_service,
    build_diabetes_risk_service,
    build_heart_risk_service,
    build_patient_health_report_service,
    build_risk_assessment_history_service,
    build_stroke_risk_service,
)
from tests.support.memory_risk_assessment_history_repository import (
    InMemoryRiskAssessmentHistoryRepository,
)
from tests.support.memory_clinical_vector_store import InMemoryClinicalVectorStore
from tests.support.clinical_child_service_factory import (
    build_appointment_service,
    build_health_measurement_analytics_service,
    build_health_measurement_service,
    build_medical_record_service,
)
from tests.support.patient_service_factory import build_policy_patient_service
from tests.support.test_auth_service import AuthServiceWithDoctorMembership


@pytest.fixture
def test_settings() -> Settings:
    """Override settings for test environment."""
    return Settings(
        ENVIRONMENT="development",
        DEBUG=True,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        AUTH_RATE_LIMIT_ENABLED=False,
        HEALTH_CHECK_DB_ENABLED=False,
        METRICS_ENABLED=False,
        SLOW_REQUEST_THRESHOLD_MS=0,
        EMBEDDING_PROVIDER="fake",
        CLINICAL_NARRATIVE_PROVIDER="fake",
        CLINICAL_NARRATIVE_RATE_LIMIT_ENABLED=False,
        EMAIL_VERIFICATION_ENFORCED=False,
        EMAIL_VERIFICATION_PEPPER="test-email-verification-pepper",
        FRONTEND_PUBLIC_URL="http://localhost:3000",
        EMAIL_PROVIDER="logging",
    )


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    """Fresh in-memory user store for each test."""
    return InMemoryUserRepository()


@pytest.fixture
def email_verification_token_repository() -> InMemoryEmailVerificationTokenRepository:
    """Fresh in-memory verification token store for each test."""
    return InMemoryEmailVerificationTokenRepository()


@pytest.fixture
def recording_email_sender() -> RecordingEmailSender:
    """Captures verification emails for assertions."""
    return RecordingEmailSender()


@pytest.fixture
def audit_log_repository() -> InMemoryAuditLogRepository:
    """Fresh in-memory audit log store for each test."""
    return InMemoryAuditLogRepository()


@pytest.fixture
def assignment_repository() -> InMemoryPatientAssignmentRepository:
    """Fresh in-memory patient assignment store for each test."""
    return InMemoryPatientAssignmentRepository()


@pytest.fixture
def consent_repository() -> InMemoryPatientConsentRepository:
    """Fresh in-memory patient consent store for each test."""
    return InMemoryPatientConsentRepository()


@pytest.fixture
def membership_repository() -> InMemoryOrganizationMembershipRepository:
    """Fresh in-memory organization membership store for each test."""
    return InMemoryOrganizationMembershipRepository()


@pytest.fixture
def organization_repository() -> InMemoryOrganizationRepository:
    """Fresh in-memory organization store for each test."""
    return InMemoryOrganizationRepository()


@pytest.fixture
def patient_repository(
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> InMemoryPatientRepository:
    """Fresh in-memory patient store for each test."""
    return InMemoryPatientRepository(assignment_repository)


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
def risk_assessment_history_repository() -> InMemoryRiskAssessmentHistoryRepository:
    """Fresh in-memory risk assessment history store for each test."""
    return InMemoryRiskAssessmentHistoryRepository()


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
    test_settings: Settings,
    user_repository: InMemoryUserRepository,
    email_verification_token_repository: InMemoryEmailVerificationTokenRepository,
    recording_email_sender: RecordingEmailSender,
    audit_log_repository: InMemoryAuditLogRepository,
    patient_repository: InMemoryPatientRepository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    organization_repository: InMemoryOrganizationRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
    consent_repository: InMemoryPatientConsentRepository,
    appointment_repository: InMemoryAppointmentRepository,
    medical_record_repository: InMemoryMedicalRecordRepository,
    health_measurement_repository: InMemoryHealthMeasurementRepository,
    risk_assessment_history_repository: InMemoryRiskAssessmentHistoryRepository,
):
    """Async HTTP client with in-memory backends for all business modules."""
    clinical_vector_store = InMemoryClinicalVectorStore()

    def override_audit_service(_request: Request) -> AuditService:
        return AuditService(audit_log_repository)

    def build_email_verification_service(request: Request) -> EmailVerificationService:
        return EmailVerificationService(
            user_repository,
            email_verification_token_repository,
            recording_email_sender,
            request.app.state.settings,
        )

    def override_email_verification_service(request: Request) -> EmailVerificationService:
        return build_email_verification_service(request)

    def override_auth_service(request: Request) -> AuthService:
        return AuthServiceWithDoctorMembership(
            user_repository,
            request.app.state.settings,
            AuditService(audit_log_repository),
            membership_repository,
            email_verification_service=build_email_verification_service(request),
        )

    def override_patient_service(_request: Request) -> PatientService:
        return build_policy_patient_service(
            patient_repository,
            membership_repository,
            assignment_repository,
        )

    def override_clinic_admin_organization_service(
        _request: Request,
    ) -> ClinicAdminOrganizationService:
        return ClinicAdminOrganizationService(
            membership_repository,
            assignment_repository,
            patient_repository,
            user_repository,
            organization_repository,
        )

    def override_patient_consent_service(_request: Request) -> PatientConsentService:
        return PatientConsentService(
            membership_repository,
            consent_repository,
            patient_repository,
        )

    def override_appointment_service(_request: Request) -> AppointmentService:
        return build_appointment_service(
            appointment_repository,
            patient_repository,
            membership_repository,
            assignment_repository,
        )

    def override_medical_record_service(_request: Request) -> MedicalRecordService:
        return build_medical_record_service(
            medical_record_repository,
            patient_repository,
            membership_repository,
            assignment_repository,
        )

    def override_health_measurement_service(_request: Request) -> HealthMeasurementService:
        return build_health_measurement_service(
            health_measurement_repository,
            patient_repository,
            membership_repository,
            assignment_repository,
        )

    def override_health_measurement_analytics_service(
        _request: Request,
    ) -> HealthMeasurementAnalyticsService:
        return build_health_measurement_analytics_service(
            health_measurement_repository,
            patient_repository,
            membership_repository,
            assignment_repository,
        )

    def override_patient_health_report_service(_request: Request) -> PatientHealthReportService:
        return build_patient_health_report_service(
            patient_repository,
            medical_record_repository,
            health_measurement_repository,
            membership_repository,
            assignment_repository,
        )

    def override_patient_clinical_timeline_service(
        _request: Request,
    ) -> PatientClinicalTimelineService:
        return build_clinical_timeline_service(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            appointment_repository,
            membership_repository,
            assignment_repository,
        )

    def override_patient_clinical_summary_service(
        _request: Request,
    ) -> PatientClinicalSummaryService:
        return build_clinical_summary_service(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            appointment_repository,
            risk_assessment_history_repository,
            membership_repository,
            assignment_repository,
        )

    def override_clinical_retrieval_service(_request: Request):
        from app.application.services.clinical_retrieval_service import ClinicalRetrievalService

        return build_clinical_retrieval_service(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            appointment_repository,
            risk_assessment_history_repository,
            membership_repository,
            assignment_repository,
            clinical_vector_store,
        )

    def override_clinical_narrative_service(_request: Request) -> ClinicalNarrativeService:
        return build_clinical_narrative_service(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            appointment_repository,
            risk_assessment_history_repository,
            membership_repository,
            assignment_repository,
            clinical_vector_store,
            settings=test_settings,
        )

    def override_diabetes_risk_assessment_service(_request: Request) -> DiabetesRiskAssessmentService:
        return build_diabetes_risk_service(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            membership_repository,
            assignment_repository,
            risk_assessment_history_repository,
        )

    def override_heart_disease_risk_assessment_service(
        _request: Request,
    ) -> HeartDiseaseRiskAssessmentService:
        return build_heart_risk_service(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            membership_repository,
            assignment_repository,
            risk_assessment_history_repository,
        )

    def override_stroke_risk_assessment_service(_request: Request) -> StrokeRiskAssessmentService:
        return build_stroke_risk_service(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            membership_repository,
            assignment_repository,
            risk_assessment_history_repository,
        )

    def override_risk_assessment_history_service(_request: Request):
        return build_risk_assessment_history_service(
            patient_repository,
            risk_assessment_history_repository,
            membership_repository,
            assignment_repository,
        )

    app.dependency_overrides[get_audit_service] = override_audit_service
    app.dependency_overrides[get_email_verification_service] = override_email_verification_service
    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_patient_service] = override_patient_service
    app.dependency_overrides[get_clinic_admin_organization_service] = (
        override_clinic_admin_organization_service
    )
    app.dependency_overrides[get_patient_consent_service] = override_patient_consent_service
    app.dependency_overrides[get_appointment_service] = override_appointment_service
    app.dependency_overrides[get_medical_record_service] = override_medical_record_service
    app.dependency_overrides[get_health_measurement_service] = override_health_measurement_service
    app.dependency_overrides[get_health_measurement_analytics_service] = (
        override_health_measurement_analytics_service
    )
    app.dependency_overrides[get_patient_health_report_service] = (
        override_patient_health_report_service
    )
    app.dependency_overrides[get_patient_clinical_timeline_service] = (
        override_patient_clinical_timeline_service
    )
    app.dependency_overrides[get_patient_clinical_summary_service] = (
        override_patient_clinical_summary_service
    )
    app.dependency_overrides[get_clinical_retrieval_service] = override_clinical_retrieval_service
    app.dependency_overrides[get_clinical_narrative_service] = override_clinical_narrative_service
    app.dependency_overrides[get_diabetes_risk_assessment_service] = (
        override_diabetes_risk_assessment_service
    )
    app.dependency_overrides[get_heart_disease_risk_assessment_service] = (
        override_heart_disease_risk_assessment_service
    )
    app.dependency_overrides[get_stroke_risk_assessment_service] = (
        override_stroke_risk_assessment_service
    )
    app.dependency_overrides[get_risk_assessment_history_service] = (
        override_risk_assessment_history_service
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

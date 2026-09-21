"""FastAPI dependency injection providers."""

from collections.abc import AsyncGenerator, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.user import UserDTO
from app.application.services.appointment_service import AppointmentService
from app.application.services.audit_service import AuditService
from app.application.services.auth_service import AuthService
from app.application.services.diabetes_risk_assessment_service import DiabetesRiskAssessmentService
from app.application.services.heart_disease_risk_assessment_service import (
    HeartDiseaseRiskAssessmentService,
)
from app.application.services.health_measurement_analytics_service import (
    HealthMeasurementAnalyticsService,
)
from app.application.services.health_measurement_service import HealthMeasurementService
from app.application.services.medical_record_service import MedicalRecordService
from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.application.services.patient_service import PatientService
from app.application.services.clinic_admin_organization_service import (
    ClinicAdminOrganizationService,
)
from app.application.services.patient_consent_service import PatientConsentService
from app.application.services.clinical_evidence_service import ClinicalEvidenceService
from app.application.services.clinical_retrieval_index_service import ClinicalRetrievalIndexService
from app.application.services.clinical_narrative_service import ClinicalNarrativeService
from app.application.services.clinical_retrieval_service import ClinicalRetrievalService
from app.application.services.patient_clinical_summary_service import (
    PatientClinicalSummaryService,
)
from app.application.services.patient_clinical_timeline_service import (
    PatientClinicalTimelineService,
)
from app.application.services.patient_health_report_service import PatientHealthReportService
from app.application.services.risk_assessment_history_service import RiskAssessmentHistoryService
from app.application.services.stroke_risk_assessment_service import StrokeRiskAssessmentService
from app.core.config import Settings
from app.core.exceptions import AppException
from app.domain.entities.user import UserRole
from app.infrastructure.database.session import get_db_session
from app.infrastructure.embeddings.embedding_factory import get_embedding_provider
from app.infrastructure.llm.narrative_generator_factory import get_clinical_narrative_generator
from app.infrastructure.repositories.appointment_repository import SQLAlchemyAppointmentRepository
from app.infrastructure.repositories.clinical_retrieval_vector_repository import (
    SQLAlchemyClinicalVectorStore,
)
from app.infrastructure.repositories.isolated_audit_log_repository import (
    IsolatedSQLAlchemyAuditLogRepository,
)
from app.infrastructure.repositories.health_measurement_repository import (
    SQLAlchemyHealthMeasurementRepository,
)
from app.infrastructure.repositories.medical_record_repository import SQLAlchemyMedicalRecordRepository
from app.infrastructure.repositories.organization_membership_repository import (
    SQLAlchemyOrganizationMembershipRepository,
)
from app.infrastructure.repositories.patient_assignment_repository import (
    SQLAlchemyPatientAssignmentRepository,
)
from app.infrastructure.repositories.patient_consent_repository import (
    SQLAlchemyPatientConsentRepository,
)
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.risk_assessment_history_repository import (
    SQLAlchemyRiskAssessmentHistoryRepository,
)
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository

_bearer_scheme = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    """Return application settings stored on the FastAPI app instance."""
    return request.app.state.settings


async def get_db_session_from_app(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a DB session using the app-scoped settings."""
    async for session in get_db_session(request.app.state.settings):
        yield session


def _patient_access_policy_bundle(
    session: AsyncSession,
) -> tuple[
    SQLAlchemyPatientRepository,
    SQLAlchemyOrganizationMembershipRepository,
    SQLAlchemyPatientAssignmentRepository,
    DefaultPatientAccessPolicy,
]:
    patient_repository = SQLAlchemyPatientRepository(session)
    membership_repository = SQLAlchemyOrganizationMembershipRepository(session)
    assignment_repository = SQLAlchemyPatientAssignmentRepository(session)
    access_policy = DefaultPatientAccessPolicy(
        patient_repository,
        membership_repository,
        assignment_repository,
    )
    return patient_repository, membership_repository, assignment_repository, access_policy


def get_patient_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> PatientService:
    """Provide a PatientService bound to the current request session."""
    (
        patient_repository,
        membership_repository,
        assignment_repository,
        access_policy,
    ) = _patient_access_policy_bundle(session)
    return PatientService(
        patient_repository,
        access_policy,
        membership_repository,
        assignment_repository,
    )


def get_appointment_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> AppointmentService:
    """Provide an AppointmentService bound to the current request session."""
    (
        patient_repository,
        membership_repository,
        assignment_repository,
        access_policy,
    ) = _patient_access_policy_bundle(session)
    return AppointmentService(
        SQLAlchemyAppointmentRepository(session),
        patient_repository,
        access_policy,
        membership_repository,
    )


def get_medical_record_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> MedicalRecordService:
    """Provide a MedicalRecordService bound to the current request session."""
    (
        patient_repository,
        membership_repository,
        assignment_repository,
        access_policy,
    ) = _patient_access_policy_bundle(session)
    return MedicalRecordService(
        SQLAlchemyMedicalRecordRepository(session),
        patient_repository,
        access_policy,
        membership_repository,
    )


def get_health_measurement_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> HealthMeasurementService:
    """Provide a HealthMeasurementService bound to the current request session."""
    (
        patient_repository,
        membership_repository,
        assignment_repository,
        access_policy,
    ) = _patient_access_policy_bundle(session)
    return HealthMeasurementService(
        SQLAlchemyHealthMeasurementRepository(session),
        patient_repository,
        access_policy,
        membership_repository,
    )


def get_stroke_risk_assessment_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> StrokeRiskAssessmentService:
    """Provide a StrokeRiskAssessmentService bound to the current request session."""
    patient_repository, _, _, access_policy = _patient_access_policy_bundle(session)
    history_repository = SQLAlchemyRiskAssessmentHistoryRepository(session)
    return StrokeRiskAssessmentService(
        patient_repository,
        SQLAlchemyHealthMeasurementRepository(session),
        SQLAlchemyMedicalRecordRepository(session),
        access_policy=access_policy,
        history_repository=history_repository,
    )


def get_heart_disease_risk_assessment_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> HeartDiseaseRiskAssessmentService:
    """Provide a HeartDiseaseRiskAssessmentService bound to the current request session."""
    patient_repository, _, _, access_policy = _patient_access_policy_bundle(session)
    history_repository = SQLAlchemyRiskAssessmentHistoryRepository(session)
    return HeartDiseaseRiskAssessmentService(
        patient_repository,
        SQLAlchemyHealthMeasurementRepository(session),
        SQLAlchemyMedicalRecordRepository(session),
        access_policy=access_policy,
        history_repository=history_repository,
    )


def get_diabetes_risk_assessment_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> DiabetesRiskAssessmentService:
    """Provide a DiabetesRiskAssessmentService bound to the current request session."""
    patient_repository, _, _, access_policy = _patient_access_policy_bundle(session)
    history_repository = SQLAlchemyRiskAssessmentHistoryRepository(session)
    return DiabetesRiskAssessmentService(
        patient_repository,
        SQLAlchemyHealthMeasurementRepository(session),
        SQLAlchemyMedicalRecordRepository(session),
        access_policy=access_policy,
        history_repository=history_repository,
    )


def get_risk_assessment_history_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> RiskAssessmentHistoryService:
    """Provide RiskAssessmentHistoryService bound to the current request session."""
    patient_repository, _, _, access_policy = _patient_access_policy_bundle(session)
    return RiskAssessmentHistoryService(
        SQLAlchemyRiskAssessmentHistoryRepository(session),
        patient_repository,
        access_policy,
    )


def get_health_measurement_analytics_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> HealthMeasurementAnalyticsService:
    """Provide a HealthMeasurementAnalyticsService bound to the current request session."""
    (
        patient_repository,
        membership_repository,
        assignment_repository,
        access_policy,
    ) = _patient_access_policy_bundle(session)
    return HealthMeasurementAnalyticsService(
        SQLAlchemyHealthMeasurementRepository(session),
        patient_repository,
        access_policy,
        membership_repository,
    )


def get_patient_health_report_service(
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    analytics_service: Annotated[
        HealthMeasurementAnalyticsService,
        Depends(get_health_measurement_analytics_service),
    ],
) -> PatientHealthReportService:
    """Provide a PatientHealthReportService composed from existing read-only services."""
    return PatientHealthReportService(
        patient_service,
        medical_record_service,
        analytics_service,
    )


def get_patient_clinical_timeline_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> PatientClinicalTimelineService:
    """Provide a PatientClinicalTimelineService composed from existing read-only services."""
    (
        patient_repository,
        membership_repository,
        _assignment_repository,
        access_policy,
    ) = _patient_access_policy_bundle(session)
    health_measurement_repository = SQLAlchemyHealthMeasurementRepository(session)
    medical_record_repository = SQLAlchemyMedicalRecordRepository(session)
    appointment_repository = SQLAlchemyAppointmentRepository(session)
    medical_record_service = MedicalRecordService(
        medical_record_repository,
        patient_repository,
        access_policy,
        membership_repository,
    )
    return PatientClinicalTimelineService(
        patient_repository,
        health_measurement_repository,
        medical_record_service,
        appointment_repository,
        DiabetesRiskAssessmentService(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            access_policy,
        ),
        HeartDiseaseRiskAssessmentService(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            access_policy,
        ),
        StrokeRiskAssessmentService(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            access_policy,
        ),
        access_policy,
    )


def get_patient_clinical_summary_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> PatientClinicalSummaryService:
    """Provide PatientClinicalSummaryService with bulk evidence loading."""
    (
        patient_repository,
        _membership_repository,
        _assignment_repository,
        access_policy,
    ) = _patient_access_policy_bundle(session)
    evidence_service = ClinicalEvidenceService(
        SQLAlchemyHealthMeasurementRepository(session),
        SQLAlchemyMedicalRecordRepository(session),
        SQLAlchemyAppointmentRepository(session),
        SQLAlchemyRiskAssessmentHistoryRepository(session),
    )
    return PatientClinicalSummaryService(
        patient_repository,
        evidence_service,
        access_policy,
    )


def get_clinical_retrieval_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ClinicalRetrievalService:
    """Provide patient-scoped clinical retrieval with pgvector index."""
    (
        patient_repository,
        _membership_repository,
        _assignment_repository,
        access_policy,
    ) = _patient_access_policy_bundle(session)
    evidence_service = ClinicalEvidenceService(
        SQLAlchemyHealthMeasurementRepository(session),
        SQLAlchemyMedicalRecordRepository(session),
        SQLAlchemyAppointmentRepository(session),
        SQLAlchemyRiskAssessmentHistoryRepository(session),
    )
    embedding_provider = get_embedding_provider(settings)
    storage_dim = settings.clinical_retrieval_vector_dimension
    vector_store = SQLAlchemyClinicalVectorStore(
        session,
        storage_vector_dimension=storage_dim,
    )
    index_service = ClinicalRetrievalIndexService(
        vector_store,
        embedding_provider,
        storage_vector_dimension=storage_dim,
    )
    return ClinicalRetrievalService(
        patient_repository,
        evidence_service,
        index_service,
        vector_store,
        embedding_provider,
        access_policy,
    )


def get_clinical_narrative_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ClinicalNarrativeService:
    """Provide RAG-backed clinical narrative generation."""
    (
        patient_repository,
        _membership_repository,
        _assignment_repository,
        access_policy,
    ) = _patient_access_policy_bundle(session)
    evidence_service = ClinicalEvidenceService(
        SQLAlchemyHealthMeasurementRepository(session),
        SQLAlchemyMedicalRecordRepository(session),
        SQLAlchemyAppointmentRepository(session),
        SQLAlchemyRiskAssessmentHistoryRepository(session),
    )
    embedding_provider = get_embedding_provider(settings)
    storage_dim = settings.clinical_retrieval_vector_dimension
    vector_store = SQLAlchemyClinicalVectorStore(
        session,
        storage_vector_dimension=storage_dim,
    )
    index_service = ClinicalRetrievalIndexService(
        vector_store,
        embedding_provider,
        storage_vector_dimension=storage_dim,
    )
    retrieval_service = ClinicalRetrievalService(
        patient_repository,
        evidence_service,
        index_service,
        vector_store,
        embedding_provider,
        access_policy,
    )
    summary_service = PatientClinicalSummaryService(
        patient_repository,
        evidence_service,
        access_policy,
    )
    narrative_generator = get_clinical_narrative_generator(settings)
    return ClinicalNarrativeService(
        patient_repository,
        retrieval_service,
        summary_service,
        narrative_generator,
        settings,
        access_policy,
    )


def get_audit_service() -> AuditService:
    """Provide an AuditService that commits audit rows in isolated transactions."""
    return AuditService(IsolatedSQLAlchemyAuditLogRepository())


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> AuthService:
    """Provide an AuthService bound to the current request session."""
    return AuthService(SQLAlchemyUserRepository(session), settings, audit_service)


# Re-export common dependencies with type aliases for route signatures
DbSession = Annotated[AsyncSession, Depends(get_db_session_from_app)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UUID:
    """Extract and validate the authenticated user ID from a JWT access token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await auth_service.resolve_access_token_user_id(credentials.credentials)
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserDTO:
    """Load the authenticated user from the database."""
    try:
        return await auth_service.get_current_user(user_id)
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
CurrentUser = Annotated[UserDTO, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[..., UserDTO]:
    """Dependency factory that restricts access to users with specific roles."""

    async def role_checker(current_user: CurrentUser) -> UserDTO:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker


ClinicalRoleGuard = Depends(require_roles(UserRole.DOCTOR, UserRole.CLINIC_ADMIN))
ClinicalUser = Annotated[UserDTO, Depends(require_roles(UserRole.DOCTOR, UserRole.CLINIC_ADMIN))]
ClinicAdminUser = Annotated[UserDTO, Depends(require_roles(UserRole.CLINIC_ADMIN))]


def get_clinic_admin_organization_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> ClinicAdminOrganizationService:
    """Provide clinic admin organization/assignment management service."""
    patient_repository, membership_repository, assignment_repository, _ = _patient_access_policy_bundle(
        session,
    )
    return ClinicAdminOrganizationService(
        membership_repository,
        assignment_repository,
        patient_repository,
    )


def get_patient_consent_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> PatientConsentService:
    """Provide clinic admin patient consent management service."""
    patient_repository, membership_repository, _, _ = _patient_access_policy_bundle(session)
    return PatientConsentService(
        membership_repository,
        SQLAlchemyPatientConsentRepository(session),
        patient_repository,
    )

"""Build clinical read/export services wired with PatientAccessPolicy for API tests."""

from app.application.services.diabetes_risk_assessment_service import DiabetesRiskAssessmentService
from app.application.services.heart_disease_risk_assessment_service import (
    HeartDiseaseRiskAssessmentService,
)
from app.application.services.medical_record_service import MedicalRecordService
from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.application.services.clinical_evidence_service import ClinicalEvidenceService
from app.application.services.clinical_retrieval_index_service import ClinicalRetrievalIndexService
from app.application.services.clinical_narrative_service import ClinicalNarrativeService
from app.application.services.clinical_retrieval_service import ClinicalRetrievalService
from app.core.config import Settings
from app.infrastructure.llm.deterministic_fake_narrative_generator import (
    DeterministicFakeNarrativeGenerator,
)
from app.infrastructure.embeddings.deterministic_fake_embedding_provider import (
    DeterministicFakeEmbeddingProvider,
)
from tests.support.memory_clinical_vector_store import InMemoryClinicalVectorStore
from app.application.services.patient_clinical_summary_service import (
    PatientClinicalSummaryService,
)
from app.application.services.patient_clinical_timeline_service import (
    PatientClinicalTimelineService,
)
from app.application.services.patient_health_report_service import PatientHealthReportService
from app.application.services.patient_service import PatientService
from app.application.services.stroke_risk_assessment_service import StrokeRiskAssessmentService
from tests.support.clinical_child_service_factory import (
    build_health_measurement_analytics_service,
    build_medical_record_service,
)
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository
from tests.support.patient_service_factory import build_policy_patient_service


def build_access_policy(
    patient_repository: InMemoryPatientRepository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> DefaultPatientAccessPolicy:
    return DefaultPatientAccessPolicy(
        patient_repository,
        membership_repository,
        assignment_repository,
    )


def build_diabetes_risk_service(
    patient_repository: InMemoryPatientRepository,
    health_measurement_repository,
    medical_record_repository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
    history_repository=None,
) -> DiabetesRiskAssessmentService:
    return DiabetesRiskAssessmentService(
        patient_repository,
        health_measurement_repository,
        medical_record_repository,
        build_access_policy(patient_repository, membership_repository, assignment_repository),
        history_repository=history_repository,
    )


def build_heart_risk_service(
    patient_repository: InMemoryPatientRepository,
    health_measurement_repository,
    medical_record_repository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
    history_repository=None,
) -> HeartDiseaseRiskAssessmentService:
    return HeartDiseaseRiskAssessmentService(
        patient_repository,
        health_measurement_repository,
        medical_record_repository,
        build_access_policy(patient_repository, membership_repository, assignment_repository),
        history_repository=history_repository,
    )


def build_stroke_risk_service(
    patient_repository: InMemoryPatientRepository,
    health_measurement_repository,
    medical_record_repository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
    history_repository=None,
) -> StrokeRiskAssessmentService:
    return StrokeRiskAssessmentService(
        patient_repository,
        health_measurement_repository,
        medical_record_repository,
        build_access_policy(patient_repository, membership_repository, assignment_repository),
        history_repository=history_repository,
    )


def build_risk_assessment_history_service(
    patient_repository: InMemoryPatientRepository,
    history_repository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
):
    from app.application.services.risk_assessment_history_service import RiskAssessmentHistoryService

    return RiskAssessmentHistoryService(
        history_repository,
        patient_repository,
        build_access_policy(patient_repository, membership_repository, assignment_repository),
    )


def build_clinical_retrieval_service(
    patient_repository: InMemoryPatientRepository,
    health_measurement_repository,
    medical_record_repository,
    appointment_repository,
    risk_assessment_history_repository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
    vector_store: InMemoryClinicalVectorStore | None = None,
) -> ClinicalRetrievalService:
    access_policy = build_access_policy(
        patient_repository,
        membership_repository,
        assignment_repository,
    )
    evidence_service = ClinicalEvidenceService(
        health_measurement_repository,
        medical_record_repository,
        appointment_repository,
        risk_assessment_history_repository,
    )
    store = vector_store or InMemoryClinicalVectorStore()
    embedding = DeterministicFakeEmbeddingProvider()
    index_service = ClinicalRetrievalIndexService(store, embedding)
    return ClinicalRetrievalService(
        patient_repository,
        evidence_service,
        index_service,
        store,
        embedding,
        access_policy,
    )


def build_clinical_narrative_service(
    patient_repository: InMemoryPatientRepository,
    health_measurement_repository,
    medical_record_repository,
    appointment_repository,
    risk_assessment_history_repository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
    vector_store: InMemoryClinicalVectorStore | None = None,
    narrative_generator=None,
    settings: Settings | None = None,
) -> ClinicalNarrativeService:
    access_policy = build_access_policy(
        patient_repository,
        membership_repository,
        assignment_repository,
    )
    retrieval = build_clinical_retrieval_service(
        patient_repository,
        health_measurement_repository,
        medical_record_repository,
        appointment_repository,
        risk_assessment_history_repository,
        membership_repository,
        assignment_repository,
        vector_store=vector_store,
    )
    summary = build_clinical_summary_service(
        patient_repository,
        health_measurement_repository,
        medical_record_repository,
        appointment_repository,
        risk_assessment_history_repository,
        membership_repository,
        assignment_repository,
    )
    generator = narrative_generator or DeterministicFakeNarrativeGenerator()
    app_settings = settings or Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        EMBEDDING_PROVIDER="fake",
        CLINICAL_NARRATIVE_PROVIDER="fake",
    )
    return ClinicalNarrativeService(
        patient_repository,
        retrieval,
        summary,
        generator,
        app_settings,
        access_policy,
    )


def build_clinical_summary_service(
    patient_repository: InMemoryPatientRepository,
    health_measurement_repository,
    medical_record_repository,
    appointment_repository,
    risk_assessment_history_repository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> PatientClinicalSummaryService:
    access_policy = build_access_policy(
        patient_repository,
        membership_repository,
        assignment_repository,
    )
    evidence_service = ClinicalEvidenceService(
        health_measurement_repository,
        medical_record_repository,
        appointment_repository,
        risk_assessment_history_repository,
    )
    return PatientClinicalSummaryService(
        patient_repository,
        evidence_service,
        access_policy,
    )


def build_clinical_timeline_service(
    patient_repository: InMemoryPatientRepository,
    health_measurement_repository,
    medical_record_repository,
    appointment_repository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> PatientClinicalTimelineService:
    access_policy = build_access_policy(
        patient_repository,
        membership_repository,
        assignment_repository,
    )
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
        build_diabetes_risk_service(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            membership_repository,
            assignment_repository,
        ),
        build_heart_risk_service(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            membership_repository,
            assignment_repository,
        ),
        build_stroke_risk_service(
            patient_repository,
            health_measurement_repository,
            medical_record_repository,
            membership_repository,
            assignment_repository,
        ),
        access_policy,
    )


def build_patient_health_report_service(
    patient_repository: InMemoryPatientRepository,
    medical_record_repository,
    health_measurement_repository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> PatientHealthReportService:
    patient_service = build_policy_patient_service(
        patient_repository,
        membership_repository,
        assignment_repository,
    )
    return PatientHealthReportService(
        patient_service,
        build_medical_record_service(
            medical_record_repository,
            patient_repository,
            membership_repository,
            assignment_repository,
        ),
        build_health_measurement_analytics_service(
            health_measurement_repository,
            patient_repository,
            membership_repository,
            assignment_repository,
        ),
    )

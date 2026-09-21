"""Import all ORM models here so Alembic autogenerate can discover them."""

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.appointment import AppointmentModel
from app.infrastructure.database.models.clinical_retrieval_vector import ClinicalRetrievalVectorModel
from app.infrastructure.database.models.audit_log import AuditLogModel
from app.infrastructure.database.models.health_measurement import HealthMeasurementModel
from app.infrastructure.database.models.medical_record import MedicalRecordModel
from app.infrastructure.database.models.organization import OrganizationModel
from app.infrastructure.database.models.organization_membership import OrganizationMembershipModel
from app.infrastructure.database.models.patient import PatientModel
from app.infrastructure.database.models.patient_assignment import PatientAssignmentModel
from app.infrastructure.database.models.patient_consent import PatientConsentModel
from app.infrastructure.database.models.risk_assessment_history import RiskAssessmentHistoryModel
from app.infrastructure.database.models.user import UserModel

__all__ = [
    "Base",
    "AppointmentModel",
    "ClinicalRetrievalVectorModel",
    "AuditLogModel",
    "HealthMeasurementModel",
    "MedicalRecordModel",
    "OrganizationModel",
    "OrganizationMembershipModel",
    "PatientAssignmentModel",
    "PatientConsentModel",
    "PatientModel",
    "RiskAssessmentHistoryModel",
    "UserModel",
]

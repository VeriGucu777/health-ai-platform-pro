"""Build clinical child resource services with patient access policy for tests."""

from app.application.services.appointment_service import AppointmentService
from app.application.services.health_measurement_analytics_service import (
    HealthMeasurementAnalyticsService,
)
from app.application.services.health_measurement_service import HealthMeasurementService
from app.application.services.medical_record_service import MedicalRecordService
from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from tests.support.memory_appointment_repository import InMemoryAppointmentRepository
from tests.support.memory_health_measurement_repository import InMemoryHealthMeasurementRepository
from tests.support.memory_medical_record_repository import InMemoryMedicalRecordRepository
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository


def _policy(
    patient_repository: InMemoryPatientRepository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> DefaultPatientAccessPolicy:
    return DefaultPatientAccessPolicy(
        patient_repository,
        membership_repository,
        assignment_repository,
    )


def build_appointment_service(
    appointment_repository: InMemoryAppointmentRepository,
    patient_repository: InMemoryPatientRepository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> AppointmentService:
    return AppointmentService(
        appointment_repository,
        patient_repository,
        _policy(patient_repository, membership_repository, assignment_repository),
        membership_repository,
    )


def build_medical_record_service(
    medical_record_repository: InMemoryMedicalRecordRepository,
    patient_repository: InMemoryPatientRepository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> MedicalRecordService:
    return MedicalRecordService(
        medical_record_repository,
        patient_repository,
        _policy(patient_repository, membership_repository, assignment_repository),
        membership_repository,
    )


def build_health_measurement_service(
    health_measurement_repository: InMemoryHealthMeasurementRepository,
    patient_repository: InMemoryPatientRepository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> HealthMeasurementService:
    return HealthMeasurementService(
        health_measurement_repository,
        patient_repository,
        _policy(patient_repository, membership_repository, assignment_repository),
        membership_repository,
    )


def build_health_measurement_analytics_service(
    health_measurement_repository: InMemoryHealthMeasurementRepository,
    patient_repository: InMemoryPatientRepository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> HealthMeasurementAnalyticsService:
    return HealthMeasurementAnalyticsService(
        health_measurement_repository,
        patient_repository,
        _policy(patient_repository, membership_repository, assignment_repository),
        membership_repository,
    )

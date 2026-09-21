"""Shared orchestration for on-demand patient risk assessments."""

from collections.abc import Callable
from datetime import datetime
from typing import TypeVar
from uuid import UUID

from app.application.analytics.risk_assessment_common import (
    ResolvedAssessmentWindow,
    filter_measurements_by_window,
    filter_medical_records_by_window,
    resolve_assessment_window,
)
from app.application.dtos.base import BaseSchema
from app.application.dtos.risk_assessment_shared import build_assessment_dto
from app.application.services.patient_read_access import resolve_patient_read_access
from app.application.services.risk_assessment_history_persistence import append_risk_assessment_history
from app.application.validators.date_range import validate_analytics_date_range
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.entities.user import UserRole
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository
from app.domain.interfaces.medical_record_repository import MedicalRecordRepository
from app.domain.interfaces.patient_access_policy import PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository
from app.domain.risk.enums import RiskAssessmentType

TAssessmentDTO = TypeVar("TAssessmentDTO", bound=BaseSchema)
TFeatures = TypeVar("TFeatures")

MEDICAL_RECORD_FETCH_LIMIT = 100


async def run_risk_assessment_for_user(
    *,
    patients: PatientRepository,
    health_measurements: HealthMeasurementRepository,
    medical_records: MedicalRecordRepository,
    access_policy: PatientAccessPolicy | None,
    actor_id: UUID,
    actor_role: UserRole,
    patient_id: UUID,
    date_from: datetime | None,
    date_to: datetime | None,
    build_feature_vector: Callable[
        [Patient, list[HealthMeasurement], list[MedicalRecord], ResolvedAssessmentWindow],
        TFeatures,
    ],
    risk_model: object,
    assessment_dto_class: type[TAssessmentDTO],
    history_repository: RiskAssessmentHistoryRepository | None = None,
    assessment_type: RiskAssessmentType | None = None,
) -> tuple[TAssessmentDTO, UUID | None]:
    """Enforce patient READ policy, then score using the patient's owner-scoped data."""
    resolved = await resolve_patient_read_access(
        patients=patients,
        access_policy=access_policy,
        actor_id=actor_id,
        actor_role=actor_role,
        patient_id=patient_id,
    )
    assessment = await run_risk_assessment_for_patient(
        health_measurements=health_measurements,
        medical_records=medical_records,
        patient=resolved.patient,
        date_from=date_from,
        date_to=date_to,
        build_feature_vector=build_feature_vector,
        risk_model=risk_model,
        assessment_dto_class=assessment_dto_class,
    )
    if history_repository is not None and assessment_type is not None:
        await append_risk_assessment_history(
            history_repository,
            patient_id=patient_id,
            organization_id=resolved.organization_id,
            assessment_type=assessment_type,
            evaluated_by_user_id=actor_id,
            assessment_dto=assessment,
        )
    return assessment, resolved.organization_id


async def run_risk_assessment_for_patient(
    *,
    health_measurements: HealthMeasurementRepository,
    medical_records: MedicalRecordRepository,
    patient: Patient,
    date_from: datetime | None,
    date_to: datetime | None,
    build_feature_vector: Callable[
        [Patient, list[HealthMeasurement], list[MedicalRecord], ResolvedAssessmentWindow],
        TFeatures,
    ],
    risk_model: object,
    assessment_dto_class: type[TAssessmentDTO],
) -> TAssessmentDTO:
    """Run a risk assessment after access was already granted (uses patient.owner_id scope)."""
    patient_id = patient.id

    window = resolve_assessment_window(date_from, date_to)
    validate_analytics_date_range(window.date_from, window.date_to)

    measurements = await health_measurements.list_by_patient_for_analytics(
        patient_id,
        date_from=window.date_from,
        date_to=window.date_to,
    )
    measurements = filter_measurements_by_window(measurements, window)

    records = await medical_records.list_by_patient_ids(
        [patient_id],
        offset=0,
        limit=MEDICAL_RECORD_FETCH_LIMIT,
        patient_id=patient_id,
    )
    records = filter_medical_records_by_window(records, window)

    features = build_feature_vector(patient, measurements, records, window)
    model_result = risk_model.assess(features)  # type: ignore[attr-defined]

    return build_assessment_dto(
        assessment_dto_class,
        patient_id=patient_id,
        date_from=window.date_from,
        date_to=window.date_to,
        model_version=risk_model.model_version,  # type: ignore[attr-defined]
        model_result=model_result,
    )

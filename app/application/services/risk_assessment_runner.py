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
from app.application.validators.date_range import validate_analytics_date_range
from app.core.exceptions import NotFoundError
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository
from app.domain.interfaces.medical_record_repository import MedicalRecordRepository
from app.domain.interfaces.patient_repository import PatientRepository

TAssessmentDTO = TypeVar("TAssessmentDTO", bound=BaseSchema)
TFeatures = TypeVar("TFeatures")

MEDICAL_RECORD_FETCH_LIMIT = 100


async def run_risk_assessment(
    *,
    patients: PatientRepository,
    health_measurements: HealthMeasurementRepository,
    medical_records: MedicalRecordRepository,
    owner_id: UUID,
    patient_id: UUID,
    date_from: datetime | None,
    date_to: datetime | None,
    build_feature_vector: Callable[
        [Patient, list[HealthMeasurement], list[MedicalRecord], ResolvedAssessmentWindow],
        TFeatures,
    ],
    risk_model: object,
    assessment_dto_class: type[TAssessmentDTO],
) -> TAssessmentDTO:
    """Load owned patient data, score with a rule model, and return an assessment DTO."""
    patient = await patients.get_by_id_and_owner(patient_id, owner_id)
    if patient is None:
        raise NotFoundError("Patient not found")

    window = resolve_assessment_window(date_from, date_to)
    validate_analytics_date_range(window.date_from, window.date_to)

    measurements = await health_measurements.list_by_owner_for_analytics(
        owner_id,
        patient_id=patient_id,
        date_from=window.date_from,
        date_to=window.date_to,
    )
    measurements = filter_measurements_by_window(measurements, window)

    records = await medical_records.list_by_owner(
        owner_id,
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

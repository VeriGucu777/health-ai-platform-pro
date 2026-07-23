"""Pure helpers for assembling heart disease risk assessment inputs."""

from __future__ import annotations

from app.application.analytics.risk_assessment_common import (
    CARDIOVASCULAR_HISTORY_RECORD_TYPES,
    ResolvedAssessmentWindow,
    build_patient_context,
    extract_average_metric,
    extract_structured_history_record_types,
    extract_structured_medical_record_types,
)
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.interfaces.heart_disease_risk_model import (
    HeartDiseaseRiskFeatureVector,
    MissingInputItem,
)


def build_feature_vector(
    patient: Patient,
    measurements: list[HealthMeasurement],
    medical_records: list[MedicalRecord],
    window: ResolvedAssessmentWindow,
) -> HeartDiseaseRiskFeatureVector:
    """Build the structured feature vector passed to the scoring model."""
    age_years, gender = build_patient_context(patient, window)
    return HeartDiseaseRiskFeatureVector(
        age_years=age_years,
        gender=gender,
        measurement_count=len(measurements),
        average_systolic_pressure=extract_average_metric(measurements, "systolic_pressure"),
        average_diastolic_pressure=extract_average_metric(measurements, "diastolic_pressure"),
        average_heart_rate=extract_average_metric(measurements, "heart_rate"),
        structured_medical_record_types=extract_structured_medical_record_types(medical_records),
        cardiovascular_history_record_types=extract_structured_history_record_types(
            medical_records,
            allowed_types=CARDIOVASCULAR_HISTORY_RECORD_TYPES,
        ),
    )


def detect_missing_inputs(features: HeartDiseaseRiskFeatureVector) -> list[MissingInputItem]:
    """Return explicit missing or incomplete inputs for the response payload."""
    missing: list[MissingInputItem] = []

    if features.average_systolic_pressure is None:
        missing.append(
            MissingInputItem(
                input="systolic_blood_pressure",
                reason="No systolic blood pressure measurements are available in the selected date range.",
                impact="A heart disease risk score cannot be computed without systolic blood pressure data.",
            )
        )

    if features.average_diastolic_pressure is None:
        missing.append(
            MissingInputItem(
                input="diastolic_blood_pressure",
                reason="No diastolic blood pressure measurements are available in the selected date range.",
                impact="A heart disease risk score cannot be computed without diastolic blood pressure data.",
            )
        )

    if features.average_heart_rate is None:
        missing.append(
            MissingInputItem(
                input="heart_rate",
                reason="No heart rate measurements are available in the selected date range.",
                impact="Assessment is computed without heart rate as a supporting factor.",
            )
        )

    missing.append(
        MissingInputItem(
            input="cholesterol",
            reason="Cholesterol is not stored as structured data in the current patient record schema.",
            impact="Assessment is computed without cholesterol as a supporting factor.",
        )
    )

    if not features.cardiovascular_history_record_types:
        missing.append(
            MissingInputItem(
                input="cardiovascular_history",
                reason=(
                    "No structured cardiovascular history record types "
                    "(cardiovascular_history or cardiology_visit) are present in the selected date range."
                ),
                impact="Assessment is computed without documented structured cardiovascular history.",
            )
        )

    return missing


def has_minimum_required_inputs(features: HeartDiseaseRiskFeatureVector) -> bool:
    """Return True when enough data exists to compute an informational score."""
    return (
        features.average_systolic_pressure is not None
        and features.average_diastolic_pressure is not None
    )

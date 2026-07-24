"""Pure helpers for assembling diabetes risk assessment inputs."""

from __future__ import annotations

from app.application.analytics.risk_assessment_common import (
    ResolvedAssessmentWindow,
    build_patient_context,
    extract_average_metric,
    extract_latest_fasting_glucose,
    extract_latest_non_fasting_glucose,
    extract_structured_medical_record_types,
)
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.interfaces.diabetes_risk_model import DiabetesRiskFeatureVector, MissingInputItem

__all__ = [
    "ResolvedAssessmentWindow",
    "build_feature_vector",
    "detect_missing_inputs",
    "has_minimum_required_inputs",
]


def build_feature_vector(
    patient: Patient,
    measurements: list[HealthMeasurement],
    medical_records: list[MedicalRecord],
    window: ResolvedAssessmentWindow,
) -> DiabetesRiskFeatureVector:
    """Build the structured feature vector passed to the scoring model."""
    age_years, gender = build_patient_context(patient, window)
    return DiabetesRiskFeatureVector(
        age_years=age_years,
        gender=gender,
        measurement_count=len(measurements),
        latest_fasting_glucose=extract_latest_fasting_glucose(measurements),
        latest_non_fasting_glucose=extract_latest_non_fasting_glucose(measurements),
        average_systolic_pressure=extract_average_metric(measurements, "systolic_pressure"),
        structured_medical_record_types=extract_structured_medical_record_types(medical_records),
    )


def detect_missing_inputs(features: DiabetesRiskFeatureVector) -> list[MissingInputItem]:
    """Return explicit missing or incomplete inputs for the response payload."""
    missing: list[MissingInputItem] = []

    if features.latest_fasting_glucose is None:
        missing.append(
            MissingInputItem(
                input="fasting_blood_glucose",
                reason="No fasting blood glucose measurement is available in the selected date range.",
                impact=(
                    "Assessment uses the latest non-fasting glucose reading when available; "
                    "fasting context improves interpretability."
                ),
            )
        )

    if (
        features.latest_fasting_glucose is None
        and features.latest_non_fasting_glucose is None
    ):
        missing.append(
            MissingInputItem(
                input="blood_glucose",
                reason="No blood glucose measurement is available in the selected date range.",
                impact="A diabetes risk score cannot be computed without at least one glucose reading.",
            )
        )

    if features.average_systolic_pressure is None:
        missing.append(
            MissingInputItem(
                input="systolic_blood_pressure",
                reason="No systolic blood pressure measurements are available in the selected date range.",
                impact="Assessment is computed without blood pressure as a supporting factor.",
            )
        )

    missing.append(
        MissingInputItem(
            input="height_cm",
            reason="Height is not recorded for this patient.",
            impact="BMI cannot be calculated; body-weight-related risk is not included.",
        )
    )

    return missing


def has_minimum_required_inputs(features: DiabetesRiskFeatureVector) -> bool:
    """Return True when enough data exists to compute an informational score."""
    return (
        features.latest_fasting_glucose is not None
        or features.latest_non_fasting_glucose is not None
    )

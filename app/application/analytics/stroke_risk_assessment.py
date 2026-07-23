"""Pure helpers for assembling stroke risk assessment inputs."""

from __future__ import annotations

from app.application.analytics.risk_assessment_common import (
    STROKE_HISTORY_RECORD_TYPES,
    ResolvedAssessmentWindow,
    build_patient_context,
    extract_average_metric,
    extract_latest_fasting_glucose,
    extract_latest_non_fasting_glucose,
    extract_structured_history_record_types,
    extract_structured_medical_record_types,
)
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.interfaces.stroke_risk_model import MissingInputItem, StrokeRiskFeatureVector


def build_feature_vector(
    patient: Patient,
    measurements: list[HealthMeasurement],
    medical_records: list[MedicalRecord],
    window: ResolvedAssessmentWindow,
) -> StrokeRiskFeatureVector:
    """Build the structured feature vector passed to the scoring model."""
    age_years, gender = build_patient_context(patient, window)
    return StrokeRiskFeatureVector(
        age_years=age_years,
        gender=gender,
        measurement_count=len(measurements),
        average_systolic_pressure=extract_average_metric(measurements, "systolic_pressure"),
        average_diastolic_pressure=extract_average_metric(measurements, "diastolic_pressure"),
        latest_fasting_glucose=extract_latest_fasting_glucose(measurements),
        latest_non_fasting_glucose=extract_latest_non_fasting_glucose(measurements),
        structured_medical_record_types=extract_structured_medical_record_types(medical_records),
        stroke_history_record_types=extract_structured_history_record_types(
            medical_records,
            allowed_types=STROKE_HISTORY_RECORD_TYPES,
        ),
    )


def detect_missing_inputs(features: StrokeRiskFeatureVector) -> list[MissingInputItem]:
    """Return explicit missing or incomplete inputs for the response payload."""
    missing: list[MissingInputItem] = []

    if features.average_systolic_pressure is None:
        missing.append(
            MissingInputItem(
                input="systolic_blood_pressure",
                reason="No systolic blood pressure measurements are available in the selected date range.",
                impact="A stroke risk score cannot be computed without systolic blood pressure data.",
            )
        )

    if features.average_diastolic_pressure is None:
        missing.append(
            MissingInputItem(
                input="diastolic_blood_pressure",
                reason="No diastolic blood pressure measurements are available in the selected date range.",
                impact="Assessment is computed without diastolic blood pressure as a supporting factor.",
            )
        )

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

    if features.latest_fasting_glucose is None and features.latest_non_fasting_glucose is None:
        missing.append(
            MissingInputItem(
                input="blood_glucose",
                reason="No blood glucose measurement is available in the selected date range.",
                impact="A stroke risk score cannot be computed without at least one glucose reading.",
            )
        )

    if not features.stroke_history_record_types:
        missing.append(
            MissingInputItem(
                input="stroke_history",
                reason=(
                    "No structured stroke or TIA history record types "
                    "(stroke_history or tia_history) are present in the selected date range."
                ),
                impact="Assessment is computed without documented structured stroke or TIA history.",
            )
        )

    return missing


def has_minimum_required_inputs(features: StrokeRiskFeatureVector) -> bool:
    """Return True when enough data exists to compute an informational score."""
    has_glucose = (
        features.latest_fasting_glucose is not None
        or features.latest_non_fasting_glucose is not None
    )
    return features.average_systolic_pressure is not None and has_glucose

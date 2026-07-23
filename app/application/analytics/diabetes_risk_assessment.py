"""Pure helpers for assembling diabetes risk assessment inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.application.analytics.health_measurement_analytics import (
    compute_metric_statistics,
    extract_metric_value,
)
from app.application.analytics.health_measurement_insights import extract_latest_measurement
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.interfaces.diabetes_risk_model import DiabetesRiskFeatureVector, MissingInputItem

STRUCTURED_MEDICAL_RECORD_TYPES: frozenset[str] = frozenset(
    {"visit", "lab_result", "imaging", "procedure", "vaccination"}
)


@dataclass(frozen=True)
class ResolvedAssessmentWindow:
    """UTC date range used for on-demand assessment."""

    date_from: datetime
    date_to: datetime


def resolve_assessment_window(
    date_from: datetime | None,
    date_to: datetime | None,
) -> ResolvedAssessmentWindow:
    """Resolve the assessment window, defaulting to the latest 30 days."""
    resolved_to = date_to or datetime.now(UTC)
    resolved_from = date_from or (resolved_to - timedelta(days=30))
    return ResolvedAssessmentWindow(date_from=resolved_from, date_to=resolved_to)


def calculate_age_years(date_of_birth: date, *, as_of: datetime) -> int:
    """Return whole-year age at the assessment end timestamp."""
    as_of_date = as_of.astimezone(UTC).date()
    years = as_of_date.year - date_of_birth.year
    had_birthday = (as_of_date.month, as_of_date.day) >= (
        date_of_birth.month,
        date_of_birth.day,
    )
    return years if had_birthday else years - 1


def filter_measurements_by_window(
    measurements: list[HealthMeasurement],
    window: ResolvedAssessmentWindow,
) -> list[HealthMeasurement]:
    """Keep measurements whose timestamps fall within the inclusive UTC window."""
    return [
        measurement
        for measurement in measurements
        if window.date_from <= measurement.measured_at <= window.date_to
    ]


def filter_medical_records_by_window(
    medical_records: list[MedicalRecord],
    window: ResolvedAssessmentWindow,
) -> list[MedicalRecord]:
    """Keep medical records whose timestamps fall within the inclusive UTC window."""
    return [
        record
        for record in medical_records
        if window.date_from <= record.record_date <= window.date_to
    ]


def extract_structured_medical_record_types(
    medical_records: list[MedicalRecord],
) -> tuple[str, ...]:
    """Return distinct structured record types without inspecting free-text fields."""
    record_types = {
        record.record_type.strip().lower()
        for record in medical_records
        if record.record_type.strip().lower() in STRUCTURED_MEDICAL_RECORD_TYPES
    }
    return tuple(sorted(record_types))


def extract_latest_fasting_glucose(
    measurements: list[HealthMeasurement],
) -> Decimal | None:
    """Return the latest fasting glucose value when available."""
    fasting_measurements = [
        measurement
        for measurement in measurements
        if measurement.blood_glucose is not None and measurement.glucose_context == "fasting"
    ]
    latest = extract_latest_measurement(fasting_measurements, "blood_glucose")
    if latest is None:
        return None
    return extract_metric_value(latest, "blood_glucose")


def extract_latest_non_fasting_glucose(
    measurements: list[HealthMeasurement],
) -> Decimal | None:
    """Return the latest glucose reading that is not explicitly fasting."""
    candidates = [
        measurement
        for measurement in measurements
        if measurement.blood_glucose is not None and measurement.glucose_context != "fasting"
    ]
    latest = extract_latest_measurement(candidates, "blood_glucose")
    if latest is None:
        return None
    return extract_metric_value(latest, "blood_glucose")


def extract_average_systolic_pressure(
    measurements: list[HealthMeasurement],
) -> Decimal | None:
    """Return the average systolic pressure when readings exist."""
    stats = compute_metric_statistics(measurements, "systolic_pressure")
    average = stats.get("average")
    if average is None:
        return None
    return Decimal(str(average))


def build_feature_vector(
    patient: Patient,
    measurements: list[HealthMeasurement],
    medical_records: list[MedicalRecord],
    window: ResolvedAssessmentWindow,
) -> DiabetesRiskFeatureVector:
    """Build the structured feature vector passed to the scoring model."""
    return DiabetesRiskFeatureVector(
        age_years=calculate_age_years(patient.date_of_birth, as_of=window.date_to),
        gender=patient.gender,
        measurement_count=len(measurements),
        latest_fasting_glucose=extract_latest_fasting_glucose(measurements),
        latest_non_fasting_glucose=extract_latest_non_fasting_glucose(measurements),
        average_systolic_pressure=extract_average_systolic_pressure(measurements),
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

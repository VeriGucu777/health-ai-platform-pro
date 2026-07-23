"""Shared helpers for on-demand cardiovascular risk assessments."""

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

STRUCTURED_MEDICAL_RECORD_TYPES: frozenset[str] = frozenset(
    {"visit", "lab_result", "imaging", "procedure", "vaccination"}
)
CARDIOVASCULAR_HISTORY_RECORD_TYPES: frozenset[str] = frozenset(
    {"cardiovascular_history", "cardiology_visit"}
)
STROKE_HISTORY_RECORD_TYPES: frozenset[str] = frozenset({"stroke_history", "tia_history"})


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


def extract_structured_history_record_types(
    medical_records: list[MedicalRecord],
    *,
    allowed_types: frozenset[str],
) -> tuple[str, ...]:
    """Return explicit structured history record types from a whitelist."""
    record_types = {
        record.record_type.strip().lower()
        for record in medical_records
        if record.record_type.strip().lower() in allowed_types
    }
    return tuple(sorted(record_types))


def extract_average_metric(
    measurements: list[HealthMeasurement],
    metric: str,
) -> Decimal | None:
    """Return the average metric value when readings exist."""
    stats = compute_metric_statistics(measurements, metric)
    average = stats.get("average")
    if average is None:
        return None
    return Decimal(str(average))


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


def build_patient_context(
    patient: Patient,
    window: ResolvedAssessmentWindow,
) -> tuple[int, str]:
    """Return age and gender for risk feature assembly."""
    return calculate_age_years(patient.date_of_birth, as_of=window.date_to), patient.gender

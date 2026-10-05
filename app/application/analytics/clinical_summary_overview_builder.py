"""Deterministic short-form clinical overview bullets from authorized evidence."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from app.application.analytics.clinical_timeline_rules import (
    IMAGING_RECORD_TYPES,
    LAB_RESULT_RECORD_TYPES,
)
from app.application.analytics.health_measurement_analytics import (
    MIN_DIRECTIONAL_TREND_SAMPLE_COUNT,
    compute_metric_statistics,
    data_period_bounds,
    extract_metric_value,
    group_blood_glucose_by_comparable_context,
    sort_measurements_chronologically,
)
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle
from app.application.dtos.clinical_summary_overview import (
    ClinicalSummaryOverviewItemDTO,
    OverviewSeverity,
)
from app.domain.entities.appointment import Appointment
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord

TrendStatus = Literal[
    "stable",
    "increasing",
    "decreasing",
    "insufficient_data",
    "recorded_no_direction",
]

_SEED_MARKER_PATTERN = re.compile(r"seed:[^\s]+", re.IGNORECASE)
_MAX_SNIPPET_LEN = 180
_VISIT_RECORD_TYPES = frozenset({"visit", "consultation", "follow_up", "follow-up"})


def build_clinical_summary_overview_items(
    bundle: ClinicalEvidenceBundle,
    *,
    as_of: datetime,
    max_items: int = 6,
) -> list[ClinicalSummaryOverviewItemDTO]:
    """Build up to ``max_items`` overview bullets without clinical inference beyond rules."""
    as_of_utc = _ensure_utc(as_of)
    measurements = sort_measurements_chronologically(bundle.health_measurements)
    records = sorted(bundle.medical_records, key=lambda row: (row.record_date, str(row.id)))

    candidates: list[ClinicalSummaryOverviewItemDTO] = []

    glucose_groups = group_blood_glucose_by_comparable_context(measurements)
    candidates.append(
        _glucose_overview_item(
            key="fasting_glucose_trend",
            label="Fasting blood glucose",
            context="fasting",
            group=glucose_groups.get("fasting", []),
        ),
    )
    candidates.append(
        _glucose_overview_item(
            key="post_meal_glucose_trend",
            label="Post-meal blood glucose",
            context="post_meal",
            group=glucose_groups.get("post_meal", []),
        ),
    )
    candidates.append(_blood_pressure_overview_item(measurements))
    candidates.append(_heart_rate_overview_item(measurements))
    candidates.append(_lab_overview_item(records))
    candidates.append(_imaging_overview_item(records))
    candidates.append(_visit_diagnosis_overview_item(records))
    candidates.append(_medication_treatment_overview_item(records))
    candidates.append(
        _upcoming_appointment_overview_item(bundle.appointments, as_of=as_of_utc),
    )

    items = [item for item in candidates if item is not None]
    return items[:max_items]


def _glucose_overview_item(
    *,
    key: str,
    label: str,
    context: str,
    group: list[HealthMeasurement],
) -> ClinicalSummaryOverviewItemDTO | None:
    if not group:
        return None
    return _metric_trend_overview_item(
        key=key,
        label=label,
        cohort=group,
        metric="blood_glucose",
        context_label=context.replace("_", "-"),
    )


def _blood_pressure_overview_item(
    measurements: list[HealthMeasurement],
) -> ClinicalSummaryOverviewItemDTO | None:
    cohort = [
        measurement
        for measurement in measurements
        if extract_metric_value(measurement, "systolic_pressure") is not None
    ]
    if not cohort:
        return None
    return _metric_trend_overview_item(
        key="blood_pressure_trend",
        label="Blood pressure",
        cohort=cohort,
        metric="systolic_pressure",
        context_label="systolic",
    )


def _heart_rate_overview_item(
    measurements: list[HealthMeasurement],
) -> ClinicalSummaryOverviewItemDTO | None:
    cohort = [
        measurement
        for measurement in measurements
        if extract_metric_value(measurement, "heart_rate") is not None
    ]
    if not cohort:
        return None
    return _metric_trend_overview_item(
        key="heart_rate_trend",
        label="Heart rate",
        cohort=cohort,
        metric="heart_rate",
        context_label="resting",
    )


def _metric_trend_overview_item(
    *,
    key: str,
    label: str,
    cohort: list[HealthMeasurement],
    metric: str,
    context_label: str,
) -> ClinicalSummaryOverviewItemDTO:
    period_start, period_end = data_period_bounds(cohort)
    count = len(cohort)
    trend_status, message, severity = _describe_trend(
        cohort,
        metric=metric,
        context_label=context_label,
    )
    return ClinicalSummaryOverviewItemDTO(
        key=key,
        severity=severity,
        label=label,
        message=message,
        trend_status=trend_status,
        source_count=count,
        data_window_start=period_start,
        data_window_end=period_end,
    )


def _describe_trend(
    cohort: list[HealthMeasurement],
    *,
    metric: str,
    context_label: str,
) -> tuple[TrendStatus, str, OverviewSeverity]:
    count = len(cohort)
    if count < MIN_DIRECTIONAL_TREND_SAMPLE_COUNT:
        if count == 2:
            return (
                "recorded_no_direction",
                (
                    f"{count} comparable {context_label} measurements recorded; "
                    "not enough data for a directional trend."
                ),
                "info",
            )
        stats = compute_metric_statistics(cohort, metric)
        latest = stats["maximum"]
        return (
            "insufficient_data",
            (
                f"{count} comparable {context_label} measurement(s) on file; "
                f"latest recorded value {latest} (informational)."
            ),
            "info",
        )

    stats = compute_metric_statistics(cohort, metric)
    direction = stats["trend_direction"]
    assert direction in {"increasing", "decreasing", "stable", "insufficient_data"}
    if direction == "insufficient_data":
        return (
            "insufficient_data",
            f"Comparable {context_label} measurements present; trend not assessed.",
            "info",
        )

    trend_status: TrendStatus = direction
    severity: OverviewSeverity = "warning" if direction == "increasing" else "info"
    direction_phrase = {
        "stable": "stable pattern",
        "increasing": "increasing pattern",
        "decreasing": "decreasing pattern",
    }[direction]
    average = stats["average"]
    message = (
        f"Based on {count} comparable {context_label} measurements, values show an "
        f"informational {direction_phrase} (average {average})."
    )
    return trend_status, message, severity


def _lab_overview_item(records: list[MedicalRecord]) -> ClinicalSummaryOverviewItemDTO | None:
    lab_records = [
        record
        for record in records
        if record.record_type.strip().lower() in LAB_RESULT_RECORD_TYPES
    ]
    if not lab_records:
        return None
    latest = max(lab_records, key=lambda row: (row.record_date, str(row.id)))
    snippet = _record_snippet(latest)
    if not snippet:
        return None
    return ClinicalSummaryOverviewItemDTO(
        key="laboratory_summary",
        severity="info",
        label="Laboratory",
        message=snippet,
        source_count=len(lab_records),
        data_window_start=latest.record_date,
        data_window_end=latest.record_date,
    )


def _imaging_overview_item(records: list[MedicalRecord]) -> ClinicalSummaryOverviewItemDTO | None:
    imaging_records = [
        record
        for record in records
        if record.record_type.strip().lower() in IMAGING_RECORD_TYPES
    ]
    if not imaging_records:
        return None
    latest = max(imaging_records, key=lambda row: (row.record_date, str(row.id)))
    snippet = _record_snippet(latest)
    if not snippet:
        return None
    return ClinicalSummaryOverviewItemDTO(
        key="imaging_summary",
        severity="info",
        label="Imaging",
        message=snippet,
        source_count=len(imaging_records),
        data_window_start=latest.record_date,
        data_window_end=latest.record_date,
    )


def _visit_diagnosis_overview_item(
    records: list[MedicalRecord],
) -> ClinicalSummaryOverviewItemDTO | None:
    visit_records = [
        record
        for record in records
        if record.record_type.strip().lower() in _VISIT_RECORD_TYPES
        and (record.diagnosis or "").strip()
    ]
    if not visit_records:
        return None
    latest = max(visit_records, key=lambda row: (row.record_date, str(row.id)))
    diagnosis = _sanitize_text((latest.diagnosis or "").strip())
    if not diagnosis:
        return None
    return ClinicalSummaryOverviewItemDTO(
        key="clinical_visit_summary",
        severity="info",
        label="Clinical visit note",
        message=diagnosis,
        source_count=len(visit_records),
        data_window_start=latest.record_date,
        data_window_end=latest.record_date,
    )


def _medication_treatment_overview_item(
    records: list[MedicalRecord],
) -> ClinicalSummaryOverviewItemDTO | None:
    with_meds = [
        record
        for record in records
        if (record.medications or "").strip() or (record.treatment or "").strip()
    ]
    if not with_meds:
        return None
    latest = max(with_meds, key=lambda row: (row.record_date, str(row.id)))
    meds = _sanitize_text((latest.medications or "").strip())
    treatment = _sanitize_text((latest.treatment or "").strip())
    detail = meds or treatment
    if meds and treatment and treatment not in meds:
        detail = f"{meds}; {treatment}"
    detail = _truncate(detail)
    if not detail:
        return None
    return ClinicalSummaryOverviewItemDTO(
        key="medication_treatment_follow_up",
        severity="info",
        label="Medication and follow-up",
        message=detail,
        source_count=len(with_meds),
        data_window_start=latest.record_date,
        data_window_end=latest.record_date,
    )


def _upcoming_appointment_overview_item(
    appointments: list[Appointment],
    *,
    as_of: datetime,
) -> ClinicalSummaryOverviewItemDTO | None:
    upcoming = [
        appointment
        for appointment in appointments
        if appointment.appointment_date >= as_of
        and appointment.status.strip().lower() not in {"cancelled", "canceled", "completed"}
    ]
    if not upcoming:
        return None
    nearest = min(upcoming, key=lambda row: (row.appointment_date, str(row.id)))
    when = nearest.appointment_date.astimezone(UTC).date().isoformat()
    appt_type = _sanitize_text(nearest.appointment_type.strip()) or "Follow-up"
    message = f"Next scheduled {appt_type.lower()} on {when} (UTC date)."
    return ClinicalSummaryOverviewItemDTO(
        key="upcoming_follow_up",
        severity="info",
        label="Upcoming follow-up",
        message=message,
        source_count=len(upcoming),
        data_window_start=nearest.appointment_date,
        data_window_end=nearest.appointment_date,
    )


def _record_snippet(record: MedicalRecord) -> str:
    parts: list[str] = []
    title = _sanitize_text((record.title or "").strip())
    if title:
        parts.append(title)
    for field in (record.diagnosis, record.description):
        text = _sanitize_text((field or "").strip())
        if text and text not in parts:
            parts.append(text)
    combined = _truncate("; ".join(parts))
    return combined


def _sanitize_text(value: str) -> str:
    cleaned = _SEED_MARKER_PATTERN.sub("", value)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


def _truncate(value: str) -> str:
    if len(value) <= _MAX_SNIPPET_LEN:
        return value
    return value[: _MAX_SNIPPET_LEN - 1].rstrip() + "…"


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def overview_items_for_determinism_check(
    items: list[ClinicalSummaryOverviewItemDTO],
) -> list[dict[str, object]]:
    """Serialize overview items for determinism comparisons."""
    return [item.model_dump(mode="json") for item in items]

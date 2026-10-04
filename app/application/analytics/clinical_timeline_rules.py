"""Mapping rules from domain records to clinical timeline events."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.application.analytics.follow_up_status import is_follow_up_overdue
from app.application.clinical_display_text import text_for_clinical_display
from app.application.analytics.health_measurement_analytics import (
    MIN_DIRECTIONAL_TREND_SAMPLE_COUNT,
    compute_metric_statistics,
    data_period_bounds,
    group_blood_glucose_by_comparable_context,
    sort_measurements_chronologically,
)
from app.core.reference_ranges import KNOWN_GLUCOSE_CONTEXTS
from app.domain.entities.appointment import Appointment
from app.domain.entities.clinical_timeline import ClinicalTimelineEvent, ClinicalTimelineSource
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord

HOSPITALIZATION_RECORD_TYPES = frozenset(
    {"hospitalization", "inpatient", "admission", "hospital_admission"},
)

APPOINTMENT_STATUS_EVENT_TYPES = {
    "scheduled": "appointment_scheduled",
    "completed": "appointment_completed",
    "cancelled": "appointment_cancelled",
    "canceled": "appointment_cancelled",
}

TREND_METRICS = ("blood_glucose", "systolic_pressure", "diastolic_pressure", "weight_kg")

LAB_RESULT_RECORD_TYPES = frozenset({"lab_result", "laboratory", "lab"})
IMAGING_RECORD_TYPES = frozenset({"imaging", "imaging_report", "radiology"})


def events_from_medical_record(record: MedicalRecord) -> list[ClinicalTimelineEvent]:
    """Build timeline events from one medical record without inferring new clinical facts."""
    occurred_at = _ensure_utc(record.record_date)
    source = ClinicalTimelineSource(kind="medical_record", id=record.id)
    events: list[ClinicalTimelineEvent] = []

    record_type = record.record_type.strip().lower()
    diagnosis_text = (record.diagnosis or "").strip()
    title_text = record.title.strip()
    description_text = (record.description or "").strip()

    if record_type in LAB_RESULT_RECORD_TYPES:
        detail = diagnosis_text or description_text or title_text or "Laboratory result recorded"
        events.append(
            ClinicalTimelineEvent(
                occurred_at=occurred_at,
                event_type="medical_record_lab_result",
                headline="Laboratory result",
                detail=detail,
                source=source,
                severity="info",
            )
        )
    elif record_type in IMAGING_RECORD_TYPES:
        detail = diagnosis_text or description_text or title_text or "Imaging report recorded"
        events.append(
            ClinicalTimelineEvent(
                occurred_at=occurred_at,
                event_type="medical_record_imaging_report",
                headline="Imaging report",
                detail=detail,
                source=source,
                severity="info",
            )
        )
    elif diagnosis_text:
        events.append(
            ClinicalTimelineEvent(
                occurred_at=occurred_at,
                event_type="medical_record_diagnosis",
                headline="Diagnosis recorded",
                detail=diagnosis_text,
                source=source,
                severity="info",
            )
        )
    elif title_text:
        events.append(
            ClinicalTimelineEvent(
                occurred_at=occurred_at,
                event_type="medical_record_diagnosis",
                headline="Clinical record",
                detail=title_text,
                source=source,
                severity="info",
            )
        )

    treatment_text = (record.treatment or "").strip()
    if treatment_text:
        events.append(
            ClinicalTimelineEvent(
                occurred_at=occurred_at,
                event_type="medical_record_treatment",
                headline="Treatment noted",
                detail=treatment_text,
                source=source,
                severity="info",
            )
        )

    medications_text = (record.medications or "").strip()
    if medications_text:
        events.append(
            ClinicalTimelineEvent(
                occurred_at=occurred_at,
                event_type="medical_record_medication",
                headline="Medications noted",
                detail=medications_text,
                source=source,
                severity="info",
            )
        )

    if _is_hospitalization_record(record):
        hospital_detail = _hospitalization_detail(record)
        events.append(
            ClinicalTimelineEvent(
                occurred_at=occurred_at,
                event_type="medical_record_hospitalization",
                headline="Hospitalization recorded",
                detail=hospital_detail,
                source=source,
                severity="info",
            )
        )

    return events


def events_from_health_measurement(measurement: HealthMeasurement) -> list[ClinicalTimelineEvent]:
    """Represent one health measurement as a timeline event."""
    parts: list[str] = []
    if measurement.blood_glucose is not None:
        context_key = (measurement.glucose_context or "").strip().lower()
        if context_key in KNOWN_GLUCOSE_CONTEXTS:
            parts.append(f"blood glucose {measurement.blood_glucose} ({context_key})")
        else:
            parts.append(f"blood glucose {measurement.blood_glucose}")
    if measurement.systolic_pressure is not None and measurement.diastolic_pressure is not None:
        parts.append(
            f"blood pressure {measurement.systolic_pressure}/"
            f"{measurement.diastolic_pressure} mmHg"
        )
    elif measurement.systolic_pressure is not None:
        parts.append(f"systolic pressure {measurement.systolic_pressure} mmHg")
    elif measurement.diastolic_pressure is not None:
        parts.append(f"diastolic pressure {measurement.diastolic_pressure} mmHg")
    if measurement.heart_rate is not None:
        parts.append(f"heart rate {measurement.heart_rate} bpm")
    if measurement.weight_kg is not None:
        parts.append(f"weight {measurement.weight_kg} kg")
    if measurement.insulin_units is not None:
        parts.append(f"insulin {measurement.insulin_units} units")
    if measurement.exercise_minutes is not None:
        parts.append(f"exercise {measurement.exercise_minutes} min")

    if not parts:
        display_notes = text_for_clinical_display(measurement.notes)
        detail = display_notes or "Health measurement recorded"
    else:
        detail = "; ".join(parts)

    return [
        ClinicalTimelineEvent(
            occurred_at=_ensure_utc(measurement.measured_at),
            event_type="health_measurement",
            headline="Health measurement",
            detail=detail,
            source=ClinicalTimelineSource(kind="health_measurement", id=measurement.id),
            severity="info",
        )
    ]


def events_from_appointment(
    appointment: Appointment,
    *,
    as_of: datetime,
) -> list[ClinicalTimelineEvent]:
    """Build appointment status events and optional overdue derived event."""
    occurred_at = _ensure_utc(appointment.appointment_date)
    source = ClinicalTimelineSource(kind="appointment", id=appointment.id)
    status_key = appointment.status.strip().lower()
    event_type = APPOINTMENT_STATUS_EVENT_TYPES.get(status_key, "appointment_status")
    headline = f"Appointment {appointment.status.strip()}"
    detail_parts = [appointment.appointment_type.strip()]
    display_notes = text_for_clinical_display(appointment.notes)
    if display_notes:
        detail_parts.append(display_notes)
    detail = " — ".join(part for part in detail_parts if part)

    events = [
        ClinicalTimelineEvent(
            occurred_at=occurred_at,
            event_type=event_type,
            headline=headline,
            detail=detail or "Appointment recorded",
            source=source,
            severity="info",
        )
    ]

    if is_follow_up_overdue(appointment, as_of=as_of):
        events.append(
            ClinicalTimelineEvent(
                occurred_at=occurred_at,
                event_type="appointment_overdue",
                headline="Follow-up overdue",
                detail=(
                    f"Follow-up date passed ({occurred_at.date().isoformat()}); "
                    "no completion record found in the system."
                ),
                source=ClinicalTimelineSource(kind="derived", id=appointment.id),
                severity="warning",
            )
        )

    return events


def derived_trend_events(
    measurements: list[HealthMeasurement],
    *,
    patient_id: UUID,
    as_of: datetime,
) -> list[ClinicalTimelineEvent]:
    """Create derived timeline items from comparable measurement groups only."""
    if not measurements:
        return []

    generated_at = _ensure_utc(as_of)
    events: list[ClinicalTimelineEvent] = []
    glucose_trend_emitted = False

    glucose_groups = group_blood_glucose_by_comparable_context(measurements)
    for context, group in glucose_groups.items():
        if len(group) < MIN_DIRECTIONAL_TREND_SAMPLE_COUNT:
            continue
        stats = compute_metric_statistics(group, "blood_glucose")
        if stats["trend_direction"] != "increasing":
            continue
        period_start, period_end = data_period_bounds(group)
        if period_start is None or period_end is None:
            continue
        count = int(stats["measurement_count"])
        average = stats["average"]
        events.append(
            ClinicalTimelineEvent(
                occurred_at=generated_at,
                event_type="measurement_trend_derived",
                headline="Blood glucose trend increasing",
                detail=_format_derived_analysis_detail(
                    generated_at=generated_at,
                    period_start=period_start,
                    period_end=period_end,
                    body=(
                        f"Comparable context: {context}. Rule-based analysis over {count} "
                        f"measurements shows an increasing pattern "
                        f"(informational average: {average})."
                    ),
                ),
                source=ClinicalTimelineSource(kind="derived", id=patient_id),
                severity="warning",
                data_window_start=period_start,
                data_window_end=period_end,
            )
        )
        glucose_trend_emitted = True

    ordered = sort_measurements_chronologically(measurements)
    for metric in (m for m in TREND_METRICS if m != "blood_glucose"):
        cohort = [
            measurement
            for measurement in ordered
            if _metric_value(measurement, metric) is not None
        ]
        if len(cohort) < MIN_DIRECTIONAL_TREND_SAMPLE_COUNT:
            continue
        stats = compute_metric_statistics(cohort, metric)
        if stats["trend_direction"] != "increasing":
            continue
        period_start, period_end = data_period_bounds(cohort)
        if period_start is None or period_end is None:
            continue
        count = int(stats["measurement_count"])
        average = stats["average"]
        events.append(
            ClinicalTimelineEvent(
                occurred_at=generated_at,
                event_type="measurement_trend_derived",
                headline=f"{metric.replace('_', ' ').title()} trend increasing",
                detail=_format_derived_analysis_detail(
                    generated_at=generated_at,
                    period_start=period_start,
                    period_end=period_end,
                    body=(
                        f"Rule-based analysis over {count} comparable measurements shows "
                        f"an increasing pattern (informational average: {average})."
                    ),
                ),
                source=ClinicalTimelineSource(kind="derived", id=patient_id),
                severity="warning",
                data_window_start=period_start,
                data_window_end=period_end,
            )
        )

    glucose_with_values = [
        measurement
        for measurement in ordered
        if _metric_value(measurement, "blood_glucose") is not None
    ]
    if len(glucose_with_values) >= 2 and not glucose_trend_emitted:
        max_group = max((len(group) for group in glucose_groups.values()), default=0)
        if max_group < MIN_DIRECTIONAL_TREND_SAMPLE_COUNT:
            period_start, period_end = data_period_bounds(glucose_with_values)
            if period_start is not None and period_end is not None:
                events.append(
                    ClinicalTimelineEvent(
                        occurred_at=generated_at,
                        event_type="measurement_trend_insufficient_comparable",
                        headline="Comparable measurements insufficient for trend",
                        detail=_format_derived_analysis_detail(
                            generated_at=generated_at,
                            period_start=period_start,
                            period_end=period_end,
                            body=(
                                "Insufficient comparable blood glucose measurements for a "
                                "directional trend. Fasting, post-meal, and unknown contexts "
                                "are not combined."
                            ),
                        ),
                        source=ClinicalTimelineSource(kind="derived", id=patient_id),
                        severity="info",
                        data_window_start=period_start,
                        data_window_end=period_end,
                    )
                )

    return events


def risk_snapshot_event(
    *,
    patient_id: UUID,
    disease: str,
    risk_level: str | None,
    score: float | None,
    model_version: str,
    assessed_at: datetime,
) -> ClinicalTimelineEvent:
    """Build a single on-demand risk snapshot event (not historical series)."""
    level_text = risk_level or "not available"
    score_text = score if score is not None else "not available"
    return ClinicalTimelineEvent(
        occurred_at=_ensure_utc(assessed_at),
        event_type="risk_current_snapshot",
        headline=f"{disease} risk snapshot (current)",
        detail=(
            f"On-demand rule-based assessment ({model_version}): "
            f"risk level {level_text}, score {score_text}. "
            "This is a point-in-time snapshot, not stored clinical history."
        ),
        source=ClinicalTimelineSource(kind="risk_assessment_current_snapshot", id=patient_id),
        severity="info" if risk_level in {None, "low"} else "warning",
    )


def _is_hospitalization_record(record: MedicalRecord) -> bool:
    record_type = record.record_type.strip().lower()
    if record_type in HOSPITALIZATION_RECORD_TYPES:
        return True
    title_lower = record.title.strip().lower()
    if "hospital" in title_lower and ("admission" in title_lower or "inpatient" in title_lower):
        return True
    description = (record.description or "").strip().lower()
    return description.startswith("hospitalization:") or description.startswith("admitted:")


def _hospitalization_detail(record: MedicalRecord) -> str:
    parts = [record.title.strip()]
    if record.hospital_name:
        parts.append(record.hospital_name.strip())
    if record.description:
        parts.append(record.description.strip())
    return " — ".join(part for part in parts if part)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _format_derived_analysis_detail(
    *,
    generated_at: datetime,
    period_start: datetime,
    period_end: datetime,
    body: str,
) -> str:
    return (
        f"Generated at {generated_at.isoformat()}. "
        f"Data period {period_start.date().isoformat()} to "
        f"{period_end.date().isoformat()} (UTC). {body}"
    )


def _metric_value(measurement: HealthMeasurement, metric: str):
    return getattr(measurement, metric, None)

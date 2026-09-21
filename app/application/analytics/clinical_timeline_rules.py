"""Mapping rules from domain records to clinical timeline events."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.application.analytics.follow_up_status import is_follow_up_overdue
from app.application.analytics.health_measurement_analytics import compute_metric_statistics
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


def events_from_medical_record(record: MedicalRecord) -> list[ClinicalTimelineEvent]:
    """Build timeline events from one medical record without inferring new clinical facts."""
    occurred_at = _ensure_utc(record.record_date)
    source = ClinicalTimelineSource(kind="medical_record", id=record.id)
    events: list[ClinicalTimelineEvent] = []

    diagnosis_text = (record.diagnosis or "").strip()
    title_text = record.title.strip()
    if diagnosis_text:
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
        context = measurement.glucose_context or "unspecified context"
        parts.append(f"blood glucose {measurement.blood_glucose} ({context})")
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
        detail = (measurement.notes or "").strip() or "Health measurement recorded"
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
    if appointment.notes:
        detail_parts.append(appointment.notes.strip())
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
                    f"Scheduled appointment on {occurred_at.date().isoformat()} "
                    f"({appointment.appointment_type}) has not been marked completed."
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
    """Create derived trend events when analytics detect increasing metrics."""
    if len(measurements) < 2:
        return []

    events: list[ClinicalTimelineEvent] = []
    measurement_ids = [str(measurement.id) for measurement in measurements]

    for metric in TREND_METRICS:
        stats = compute_metric_statistics(measurements, metric)
        if stats["trend_direction"] != "increasing":
            continue
        count = int(stats["measurement_count"])
        if count < 2:
            continue
        average = stats["average"]
        events.append(
            ClinicalTimelineEvent(
                occurred_at=_ensure_utc(as_of),
                event_type="measurement_trend_derived",
                headline=f"{metric.replace('_', ' ').title()} trend increasing",
                detail=(
                    f"Rule-based trend analysis over {count} measurements in the selected "
                    f"period shows an increasing pattern (informational average: {average}). "
                    f"Related measurement IDs: {', '.join(measurement_ids[:10])}"
                    f"{'...' if len(measurement_ids) > 10 else ''}."
                ),
                source=ClinicalTimelineSource(kind="derived", id=patient_id),
                severity="warning",
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

"""Deterministic PHI-minimized canonical text for clinical retrieval."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.application.analytics.health_measurement_analytics import extract_metric_value
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle, ClinicalRetrievalDocumentDTO
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.appointment import Appointment
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory

_PHI_KEYS = frozenset(
    {
        "first_name",
        "last_name",
        "phone",
        "date_of_birth",
        "email",
        "owner_id",
        "patient_id",
    }
)

_MEASUREMENT_METRICS = (
    "blood_glucose",
    "systolic_pressure",
    "diastolic_pressure",
    "heart_rate",
    "weight_kg",
    "insulin_units",
    "exercise_minutes",
)


def build_canonical_text(
    doc: ClinicalRetrievalDocumentDTO,
    bundle: ClinicalEvidenceBundle,
) -> str:
    """Serialize one evidence document to stable canonical text without patient demographics."""
    source_type = doc.source_type
    source_id = doc.source_id
    payload: dict[str, Any] = {"source_type": source_type.value, "source_id": str(source_id)}
    if doc.event_time is not None:
        payload["event_time"] = doc.event_time.isoformat()

    if source_type == ClinicalEvidenceSourceType.MEDICAL_RECORD:
        record = _find_medical_record(bundle, source_id)
        if record is not None:
            _apply_medical_record(payload, record)
    elif source_type == ClinicalEvidenceSourceType.HEALTH_MEASUREMENT:
        measurement = _find_measurement(bundle, source_id)
        if measurement is not None:
            _apply_measurement(payload, measurement)
    elif source_type == ClinicalEvidenceSourceType.APPOINTMENT:
        appointment = _find_appointment(bundle, source_id)
        if appointment is not None:
            _apply_appointment(payload, appointment)
    elif source_type == ClinicalEvidenceSourceType.RISK_ASSESSMENT_HISTORY:
        row = _find_risk_history(bundle, source_id)
        if row is not None:
            _apply_risk_history(payload, row)
    else:
        payload["content_fields"] = _sanitize_content_fields(doc.content_fields)

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sanitize_content_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in fields.items() if k not in _PHI_KEYS}


def _apply_medical_record(payload: dict[str, Any], record: MedicalRecord) -> None:
    payload["record_type"] = record.record_type
    payload["title"] = record.title
    if record.diagnosis:
        payload["diagnosis"] = record.diagnosis.strip()
    if record.treatment:
        payload["treatment"] = record.treatment.strip()
    if record.medications:
        payload["medications"] = record.medications.strip()
    if record.description:
        payload["description"] = record.description.strip()
    if record.hospital_name:
        payload["hospital_name"] = record.hospital_name.strip()


def _apply_measurement(payload: dict[str, Any], measurement: HealthMeasurement) -> None:
    payload["measured_at"] = measurement.measured_at.isoformat()
    metrics: dict[str, str] = {}
    for name in _MEASUREMENT_METRICS:
        value = extract_metric_value(measurement, name)
        if value is not None:
            metrics[name] = str(value)
    if measurement.glucose_context:
        metrics["glucose_context"] = measurement.glucose_context
    if measurement.meal_context:
        metrics["meal_context"] = measurement.meal_context
    payload["metrics"] = metrics


def _apply_appointment(payload: dict[str, Any], appointment: Appointment) -> None:
    payload["appointment_type"] = appointment.appointment_type
    payload["status"] = appointment.status
    payload["appointment_date"] = appointment.appointment_date.isoformat()


def _apply_risk_history(payload: dict[str, Any], row: RiskAssessmentHistory) -> None:
    payload["assessment_type"] = row.assessment_type.value
    payload["assessment_status"] = row.assessment_status
    payload["model_kind"] = row.model_kind
    payload["model_version"] = row.model_version
    if row.risk_level is not None:
        payload["risk_level"] = row.risk_level
    if row.score is not None:
        payload["score"] = row.score
    if row.probability is not None:
        payload["probability"] = row.probability


def _find_medical_record(bundle: ClinicalEvidenceBundle, source_id: UUID) -> MedicalRecord | None:
    for row in bundle.medical_records:
        if row.id == source_id:
            return row
    return None


def _find_measurement(bundle: ClinicalEvidenceBundle, source_id: UUID) -> HealthMeasurement | None:
    for row in bundle.health_measurements:
        if row.id == source_id:
            return row
    return None


def _find_appointment(bundle: ClinicalEvidenceBundle, source_id: UUID) -> Appointment | None:
    for row in bundle.appointments:
        if row.id == source_id:
            return row
    return None


def _find_risk_history(bundle: ClinicalEvidenceBundle, source_id: UUID) -> RiskAssessmentHistory | None:
    for row in bundle.risk_assessment_history:
        if row.id == source_id:
            return row
    return None


def content_fields_from_canonical(canonical_text: str) -> dict[str, str]:
    """Extract structured fields for API response (string values only)."""
    data = json.loads(canonical_text)
    out: dict[str, str] = {}
    for key, value in data.items():
        if key in ("source_type", "source_id", "event_time"):
            continue
        if isinstance(value, (str, int, float, bool)):
            out[key] = str(value)
        elif isinstance(value, dict):
            out[key] = json.dumps(value, sort_keys=True)
    return out

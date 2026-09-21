"""Deterministic clinical summary from an authorized evidence bundle."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.application.analytics.follow_up_status import is_follow_up_overdue
from app.application.analytics.health_measurement_analytics import extract_metric_value
from app.application.analytics.clinical_timeline_rules import HOSPITALIZATION_RECORD_TYPES
from app.application.clinical_summary.constants import SUMMARY_VERSION
from app.application.dtos.clinical_evidence import (
    ClinicalEvidenceBundle,
    ClinicalEvidenceProvenanceDTO,
)
from app.application.dtos.patient_clinical_summary import (
    CareFlagDTO,
    ClinicalItemDTO,
    ClinicalSummaryDataQualityDTO,
    ClinicalSummaryDataWindowDTO,
    EncounterDTO,
    LatestRiskAssessmentDTO,
    PatientClinicalSummaryDTO,
    RecentMeasurementDTO,
)
from app.core.reference_ranges import CLINICAL_SUMMARY_DISCLAIMER, METRIC_REFERENCE_RANGES
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.appointment import Appointment
from app.domain.entities.medical_record import MedicalRecord
from app.domain.risk.enums import RiskAssessmentType

METRIC_UNITS: dict[str, str] = {
    "blood_glucose": "mg/dL",
    "systolic_pressure": "mmHg",
    "diastolic_pressure": "mmHg",
    "heart_rate": "bpm",
    "weight_kg": "kg",
    "insulin_units": "units",
    "exercise_minutes": "minutes",
}


def build_deterministic_clinical_summary(
    bundle: ClinicalEvidenceBundle,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    generated_at: datetime,
) -> PatientClinicalSummaryDTO:
    """Build structured summary without clinical inference."""
    clinical_items = _build_clinical_items(bundle.medical_records)
    recent_measurements = _build_recent_measurements(bundle.health_measurements)
    encounters = _build_encounters(bundle.appointments, as_of=generated_at)
    latest_risks = _build_latest_risk_assessments(bundle.risk_assessment_history)
    care_flags = _build_care_flags(
        bundle.appointments,
        latest_risks,
        bundle.health_measurements,
        as_of=generated_at,
    )
    data_quality = _build_data_quality(
        bundle,
        clinical_items=clinical_items,
        recent_measurements=recent_measurements,
        encounters=encounters,
        latest_risks=latest_risks,
    )

    return PatientClinicalSummaryDTO(
        patient_id=bundle.patient.id,
        generated_at=generated_at,
        summary_version=SUMMARY_VERSION,
        data_window=ClinicalSummaryDataWindowDTO(date_from=date_from, date_to=date_to),
        clinical_items=clinical_items,
        recent_measurements=recent_measurements,
        encounters=encounters,
        latest_risk_assessments=latest_risks,
        care_flags=care_flags,
        data_quality=data_quality,
        disclaimer=CLINICAL_SUMMARY_DISCLAIMER,
    )


def _build_clinical_items(records: list[MedicalRecord]) -> list[ClinicalItemDTO]:
    items: list[ClinicalItemDTO] = []
    seen: set[tuple[str, UUID, str, str]] = set()

    for record in sorted(records, key=lambda r: (r.record_date, str(r.id))):
        provenance = ClinicalEvidenceProvenanceDTO(
            source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
            source_id=record.id,
            occurred_at=record.record_date,
        )
        record_type = record.record_type.strip().lower()

        if record_type in HOSPITALIZATION_RECORD_TYPES:
            detail = (record.description or record.title or "").strip()
            if detail:
                _append_item(
                    items,
                    seen,
                    item_type="hospitalization",
                    label="Hospitalization record",
                    detail=detail,
                    provenance=provenance,
                )

        diagnosis = (record.diagnosis or "").strip()
        if diagnosis:
            _append_item(
                items,
                seen,
                item_type="diagnosis",
                label="Diagnosis recorded",
                detail=diagnosis,
                provenance=provenance,
            )

        treatment = (record.treatment or "").strip()
        if treatment:
            _append_item(
                items,
                seen,
                item_type="treatment",
                label="Treatment noted",
                detail=treatment,
                provenance=provenance,
            )

        medications = (record.medications or "").strip()
        if medications:
            _append_item(
                items,
                seen,
                item_type="medication",
                label="Medications noted",
                detail=medications,
                provenance=provenance,
            )

    return items


def _append_item(
    items: list[ClinicalItemDTO],
    seen: set[tuple[str, UUID, str, str]],
    *,
    item_type: str,
    label: str,
    detail: str,
    provenance: ClinicalEvidenceProvenanceDTO,
) -> None:
    key = (item_type, provenance.source_id, label, detail)
    if key in seen:
        return
    seen.add(key)
    items.append(
        ClinicalItemDTO(
            item_type=item_type,
            label=label,
            detail=detail,
            provenance=provenance,
        ),
    )


def _build_recent_measurements(
    measurements: list,
) -> list[RecentMeasurementDTO]:
    rows: list[RecentMeasurementDTO] = []
    for measurement in sorted(
        measurements,
        key=lambda m: (m.measured_at, str(m.id)),
        reverse=True,
    ):
        for metric in (
            "blood_glucose",
            "systolic_pressure",
            "diastolic_pressure",
            "heart_rate",
            "weight_kg",
            "insulin_units",
            "exercise_minutes",
        ):
            value = extract_metric_value(measurement, metric)
            if value is None:
                continue
            unit = METRIC_REFERENCE_RANGES.get(metric)
            unit_str = unit.unit if unit else METRIC_UNITS.get(metric, "")
            rows.append(
                RecentMeasurementDTO(
                    metric_type=metric,
                    value=str(value),
                    unit=unit_str,
                    measured_at=measurement.measured_at,
                    provenance=ClinicalEvidenceProvenanceDTO(
                        source_type=ClinicalEvidenceSourceType.HEALTH_MEASUREMENT,
                        source_id=measurement.id,
                        occurred_at=measurement.measured_at,
                    ),
                ),
            )
    return rows


def _build_encounters(
    appointments: list[Appointment],
    *,
    as_of: datetime,
) -> list[EncounterDTO]:
    result: list[EncounterDTO] = []
    as_of_utc = as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)

    for appointment in sorted(
        appointments,
        key=lambda a: (a.appointment_date, str(a.id)),
        reverse=True,
    ):
        status = appointment.status.strip().lower()
        timing = "future" if appointment.appointment_date >= as_of_utc else "past"
        overdue = is_follow_up_overdue(appointment, as_of=as_of_utc)
        display_status = status
        if overdue:
            display_status = "overdue"

        result.append(
            EncounterDTO(
                appointment_id=appointment.id,
                appointment_date=appointment.appointment_date,
                appointment_type=appointment.appointment_type,
                status=display_status,
                timing=timing,
                provenance=ClinicalEvidenceProvenanceDTO(
                    source_type=ClinicalEvidenceSourceType.APPOINTMENT,
                    source_id=appointment.id,
                    occurred_at=appointment.appointment_date,
                ),
            ),
        )
    return result


def _build_latest_risk_assessments(
    history: list,
) -> list[LatestRiskAssessmentDTO]:
    latest: dict[RiskAssessmentType, LatestRiskAssessmentDTO] = {}
    for row in history:
        if row.assessment_type in latest:
            continue
        latest[row.assessment_type] = LatestRiskAssessmentDTO(
            assessment_type=row.assessment_type.value,
            assessment_status=row.assessment_status,
            risk_level=row.risk_level,
            score=row.score,
            probability=row.probability,
            evaluated_at=row.evaluated_at,
            model_kind=row.model_kind,
            model_version=row.model_version,
            provenance=ClinicalEvidenceProvenanceDTO(
                source_type=ClinicalEvidenceSourceType.RISK_ASSESSMENT_HISTORY,
                source_id=row.id,
                occurred_at=row.evaluated_at,
            ),
        )
    order = (
        RiskAssessmentType.DIABETES,
        RiskAssessmentType.HEART_DISEASE,
        RiskAssessmentType.STROKE,
    )
    return [latest[t] for t in order if t in latest]


def _build_care_flags(
    appointments: list[Appointment],
    latest_risks: list[LatestRiskAssessmentDTO],
    measurements: list,
    *,
    as_of: datetime,
) -> list[CareFlagDTO]:
    flags: list[CareFlagDTO] = []
    as_of_utc = as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)

    for appointment in appointments:
        if is_follow_up_overdue(appointment, as_of=as_of_utc):
            flags.append(
                CareFlagDTO(
                    flag_type="overdue_appointment",
                    message="Scheduled appointment date is in the past.",
                    provenance=ClinicalEvidenceProvenanceDTO(
                        source_type=ClinicalEvidenceSourceType.APPOINTMENT,
                        source_id=appointment.id,
                        occurred_at=appointment.appointment_date,
                    ),
                ),
            )
            break

    for risk in latest_risks:
        if risk.assessment_status == "insufficient_data":
            flags.append(
                CareFlagDTO(
                    flag_type="incomplete_risk_assessment",
                    message=f"{risk.assessment_type} assessment has insufficient data.",
                    provenance=risk.provenance,
                ),
            )

    if not measurements:
        flags.append(
            CareFlagDTO(
                flag_type="missing_recent_measurement",
                message="No health measurements available in the selected window.",
                provenance=None,
            ),
        )

    return flags


def _build_data_quality(
    bundle: ClinicalEvidenceBundle,
    *,
    clinical_items: list[ClinicalItemDTO],
    recent_measurements: list[RecentMeasurementDTO],
    encounters: list[EncounterDTO],
    latest_risks: list[LatestRiskAssessmentDTO],
) -> ClinicalSummaryDataQualityDTO:
    sections = {
        "clinical_items": bool(clinical_items),
        "recent_measurements": bool(recent_measurements),
        "encounters": bool(encounters),
        "latest_risk_assessments": bool(latest_risks),
    }
    missing = [name for name, present in sections.items() if not present]
    no_data = not any(sections.values())

    last_dates: list[datetime] = []
    for record in bundle.medical_records:
        last_dates.append(record.record_date)
    for measurement in bundle.health_measurements:
        last_dates.append(measurement.measured_at)
    for appointment in bundle.appointments:
        last_dates.append(appointment.appointment_date)
    for row in bundle.risk_assessment_history:
        last_dates.append(row.evaluated_at)

    last_available = max(last_dates) if last_dates else None
    return ClinicalSummaryDataQualityDTO(
        no_data=no_data,
        missing_sections=missing,
        last_available_date=last_available,
        stale_sections=[],
    )


def summary_content_for_determinism_check(dto: PatientClinicalSummaryDTO) -> dict[str, Any]:
    """Serialize summary for determinism tests (excludes generated_at)."""
    data = dto.model_dump(mode="json")
    data.pop("generated_at", None)
    return data

"""Deterministic short-form clinical overview bullets from authorized evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable, Literal

from app.application.analytics.clinical_summary_focus import SummaryFocus, infer_clinical_summary_focus
from app.application.analytics.clinical_summary_record_presentation import (
    extract_lipid_panel_values,
    is_brain_imaging_record,
    is_echocardiography_record,
    record_text_blob,
    sanitize_clinical_summary_text,
    sanitized_medication_or_treatment,
)
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

_MAX_SNIPPET_LEN = 180
_VISIT_RECORD_TYPES = frozenset({"visit", "consultation", "follow_up", "follow-up"})
_INTERNAL_TEXT_MARKERS = ("synthetic", "fictional", "demo values", "chart review", "decision-support review")

ItemBuilder = Callable[[], ClinicalSummaryOverviewItemDTO | None]


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
    glucose_groups = group_blood_glucose_by_comparable_context(measurements)
    focus = infer_clinical_summary_focus(bundle)

    ctx = _BuilderContext(
        measurements=measurements,
        records=records,
        appointments=bundle.appointments,
        glucose_groups=glucose_groups,
        as_of=as_of_utc,
    )

    builders = _builders_for_focus(focus, ctx)
    items: list[ClinicalSummaryOverviewItemDTO] = []
    for build in builders:
        item = build()
        if item is not None:
            items.append(item)
        if len(items) >= max_items:
            break
    return items[:max_items]


class _BuilderContext:
    def __init__(
        self,
        *,
        measurements: list[HealthMeasurement],
        records: list[MedicalRecord],
        appointments: list[Appointment],
        glucose_groups: dict[str, list[HealthMeasurement]],
        as_of: datetime,
    ) -> None:
        self.measurements = measurements
        self.records = records
        self.appointments = appointments
        self.glucose_groups = glucose_groups
        self.as_of = as_of


def _builders_for_focus(focus: SummaryFocus, ctx: _BuilderContext) -> list[ItemBuilder]:
    if focus == "cardiac":
        return [
            lambda: _blood_pressure_overview_item(ctx.measurements),
            lambda: _heart_rate_overview_item(ctx.measurements, cardiac_focus=True),
            lambda: _lab_overview_item(ctx.records, cardiac_focus=True),
            lambda: _imaging_overview_item(ctx.records, cardiac_focus=True),
            lambda: _medication_treatment_overview_item(ctx.records),
            lambda: _upcoming_appointment_overview_item(ctx.appointments, as_of=ctx.as_of),
            lambda: _glucose_overview_item(
                key="fasting_glucose_trend",
                label="Fasting blood glucose",
                context="fasting",
                group=ctx.glucose_groups.get("fasting", []),
            ),
            lambda: _glucose_overview_item(
                key="post_meal_glucose_trend",
                label="Post-meal blood glucose",
                context="post_meal",
                group=ctx.glucose_groups.get("post_meal", []),
            ),
        ]
    if focus == "stroke":
        return [
            lambda: _blood_pressure_overview_item(ctx.measurements),
            lambda: _glucose_overview_item(
                key="fasting_glucose_trend",
                label="Fasting blood glucose",
                context="fasting",
                group=ctx.glucose_groups.get("fasting", []),
            ),
            lambda: _visit_diagnosis_overview_item(ctx.records),
            lambda: _imaging_overview_item(ctx.records, cardiac_focus=False),
            lambda: _medication_treatment_overview_item(ctx.records),
            lambda: _upcoming_appointment_overview_item(ctx.appointments, as_of=ctx.as_of),
            lambda: _glucose_overview_item(
                key="post_meal_glucose_trend",
                label="Post-meal blood glucose",
                context="post_meal",
                group=ctx.glucose_groups.get("post_meal", []),
            ),
        ]
    if focus == "diabetes":
        return [
            lambda: _glucose_overview_item(
                key="fasting_glucose_trend",
                label="Fasting blood glucose",
                context="fasting",
                group=ctx.glucose_groups.get("fasting", []),
            ),
            lambda: _glucose_overview_item(
                key="post_meal_glucose_trend",
                label="Post-meal blood glucose",
                context="post_meal",
                group=ctx.glucose_groups.get("post_meal", []),
            ),
            lambda: _blood_pressure_overview_item(ctx.measurements),
            lambda: _lab_overview_item(ctx.records, cardiac_focus=False),
            lambda: _medication_treatment_overview_item(ctx.records),
            lambda: _upcoming_appointment_overview_item(ctx.appointments, as_of=ctx.as_of),
            lambda: _heart_rate_overview_item(ctx.measurements, cardiac_focus=False),
            lambda: _imaging_overview_item(ctx.records, cardiac_focus=False),
            lambda: _visit_diagnosis_overview_item(ctx.records),
        ]

    return [
        lambda: _glucose_overview_item(
            key="fasting_glucose_trend",
            label="Fasting blood glucose",
            context="fasting",
            group=ctx.glucose_groups.get("fasting", []),
        ),
        lambda: _glucose_overview_item(
            key="post_meal_glucose_trend",
            label="Post-meal blood glucose",
            context="post_meal",
            group=ctx.glucose_groups.get("post_meal", []),
        ),
        lambda: _blood_pressure_overview_item(ctx.measurements),
        lambda: _heart_rate_overview_item(ctx.measurements, cardiac_focus=False),
        lambda: _lab_overview_item(ctx.records, cardiac_focus=False),
        lambda: _imaging_overview_item(ctx.records, cardiac_focus=False),
        lambda: _visit_diagnosis_overview_item(ctx.records),
        lambda: _medication_treatment_overview_item(ctx.records),
        lambda: _upcoming_appointment_overview_item(ctx.appointments, as_of=ctx.as_of),
    ]


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
    *,
    cardiac_focus: bool,
) -> ClinicalSummaryOverviewItemDTO | None:
    cohort = [
        measurement
        for measurement in measurements
        if extract_metric_value(measurement, "heart_rate") is not None
    ]
    if not cohort:
        return None
    period_start, period_end = data_period_bounds(cohort)
    count = len(cohort)
    if cardiac_focus and count < MIN_DIRECTIONAL_TREND_SAMPLE_COUNT:
        return ClinicalSummaryOverviewItemDTO(
            key="heart_rate_trend",
            severity="info",
            label="Heart rate",
            message="Resting heart rate measurements are on file; insufficient comparable data for a directional trend.",
            message_key="heart_rate_monitoring_insufficient_trend",
            trend_status="insufficient_data",
            source_count=count,
            data_window_start=period_start,
            data_window_end=period_end,
        )
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


def _lab_overview_item(
    records: list[MedicalRecord],
    *,
    cardiac_focus: bool,
) -> ClinicalSummaryOverviewItemDTO | None:
    lab_records = [
        record
        for record in records
        if record.record_type.strip().lower() in LAB_RESULT_RECORD_TYPES
    ]
    if not lab_records:
        return None
    latest = max(lab_records, key=lambda row: (row.record_date, str(row.id)))
    blob = record_text_blob(latest)
    lipids = extract_lipid_panel_values(blob)
    if lipids is not None:
        params = {"ldl": lipids.ldl, "hdl": lipids.hdl}
        message = f"Lipid panel: LDL {lipids.ldl} mg/dL, HDL {lipids.hdl} mg/dL"
        message_key = "lipid_panel_summary"
        if lipids.triglycerides:
            params["triglycerides"] = lipids.triglycerides
            message = (
                f"Lipid panel: LDL {lipids.ldl} mg/dL, HDL {lipids.hdl} mg/dL, "
                f"triglycerides {lipids.triglycerides} mg/dL"
            )
            message_key = "lipid_panel_with_triglycerides"
        return ClinicalSummaryOverviewItemDTO(
            key="laboratory_summary",
            severity="info",
            label="Laboratory",
            message=message,
            message_key=message_key,
            message_params=params,
            source_count=len(lab_records),
            data_window_start=latest.record_date,
            data_window_end=latest.record_date,
        )

    snippet = _safe_record_snippet(latest)
    if not snippet:
        return None if cardiac_focus else None
    return ClinicalSummaryOverviewItemDTO(
        key="laboratory_summary",
        severity="info",
        label="Laboratory",
        message=snippet,
        message_key="laboratory_on_file" if cardiac_focus else None,
        message_params={"detail": snippet} if cardiac_focus and snippet else {},
        source_count=len(lab_records),
        data_window_start=latest.record_date,
        data_window_end=latest.record_date,
    )


def _imaging_overview_item(
    records: list[MedicalRecord],
    *,
    cardiac_focus: bool,
) -> ClinicalSummaryOverviewItemDTO | None:
    imaging_records = [
        record
        for record in records
        if record.record_type.strip().lower() in IMAGING_RECORD_TYPES
    ]
    if not imaging_records:
        return None
    latest = max(imaging_records, key=lambda row: (row.record_date, str(row.id)))

    if is_echocardiography_record(latest):
        return ClinicalSummaryOverviewItemDTO(
            key="imaging_summary",
            severity="info",
            label="Imaging",
            message="Echocardiography report is documented in clinical records.",
            message_key="echocardiography_on_file",
            source_count=len(imaging_records),
            data_window_start=latest.record_date,
            data_window_end=latest.record_date,
        )

    if is_brain_imaging_record(latest):
        snippet = _safe_record_snippet(latest)
        if snippet and not _contains_internal_markers(snippet):
            return ClinicalSummaryOverviewItemDTO(
                key="imaging_summary",
                severity="info",
                label="Imaging",
                message=snippet,
                message_key="brain_imaging_summary",
                message_params={"detail": snippet},
                source_count=len(imaging_records),
                data_window_start=latest.record_date,
                data_window_end=latest.record_date,
            )

    snippet = _safe_record_snippet(latest)
    if not snippet or (cardiac_focus and _contains_internal_markers(snippet)):
        if cardiac_focus:
            return ClinicalSummaryOverviewItemDTO(
                key="imaging_summary",
                severity="info",
                label="Imaging",
                message="Imaging report is documented in clinical records.",
                message_key="imaging_report_on_file",
                source_count=len(imaging_records),
                data_window_start=latest.record_date,
                data_window_end=latest.record_date,
            )
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
    diagnosis = _safe_record_snippet_from_fields(latest.diagnosis or "")
    if not diagnosis:
        return None
    return ClinicalSummaryOverviewItemDTO(
        key="clinical_visit_summary",
        severity="info",
        label="Clinical visit note",
        message=diagnosis,
        message_key="clinical_visit_summary",
        message_params={"detail": diagnosis},
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
    detail = _truncate(sanitized_medication_or_treatment(latest))
    if not detail or _contains_internal_markers(detail):
        return ClinicalSummaryOverviewItemDTO(
            key="medication_treatment_follow_up",
            severity="info",
            label="Medication and follow-up",
            message="Medication and follow-up plan documented in clinical records.",
            message_key="medication_plan_on_file",
            source_count=len(with_meds),
            data_window_start=latest.record_date,
            data_window_end=latest.record_date,
        )
    return ClinicalSummaryOverviewItemDTO(
        key="medication_treatment_follow_up",
        severity="info",
        label="Medication and follow-up",
        message=detail,
        message_key="medication_treatment_summary",
        message_params={"detail": detail},
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
    appt_type = sanitize_clinical_summary_text(nearest.appointment_type.strip()) or "Follow-up"
    message = f"Next scheduled {appt_type.lower()} on {when} (UTC date)."
    return ClinicalSummaryOverviewItemDTO(
        key="upcoming_follow_up",
        severity="info",
        label="Upcoming follow-up",
        message=message,
        message_key="upcoming_follow_up_date",
        message_params={"date": when, "appointment_type": appt_type},
        source_count=len(upcoming),
        data_window_start=nearest.appointment_date,
        data_window_end=nearest.appointment_date,
    )


def _safe_record_snippet(record: MedicalRecord) -> str:
    parts: list[str] = []
    title = _safe_record_snippet_from_fields(record.title or "")
    if title:
        parts.append(title)
    for field in (record.diagnosis, record.description):
        text = _safe_record_snippet_from_fields(field or "")
        if text and text not in parts:
            parts.append(text)
    combined = _truncate("; ".join(parts))
    if _contains_internal_markers(combined):
        return ""
    return combined


def _safe_record_snippet_from_fields(value: str) -> str:
    return sanitize_clinical_summary_text(value.strip())


def _contains_internal_markers(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _INTERNAL_TEXT_MARKERS)


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

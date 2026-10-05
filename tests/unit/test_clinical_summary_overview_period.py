"""Unit tests for overview clinical period aggregation."""

from datetime import UTC, datetime

from app.application.analytics.clinical_summary_overview_period import (
    compute_overview_clinical_period,
)
from app.application.dtos.clinical_summary_overview import ClinicalSummaryOverviewItemDTO


def _item(
    key: str,
    *,
    start: datetime | None,
    end: datetime | None,
) -> ClinicalSummaryOverviewItemDTO:
    return ClinicalSummaryOverviewItemDTO(
        key=key,
        severity="info",
        label="Test",
        message="Test message",
        data_window_start=start,
        data_window_end=end,
    )


def test_period_min_max_from_non_appointment_items() -> None:
    start_a = datetime(2026, 6, 15, tzinfo=UTC)
    end_a = datetime(2026, 8, 22, tzinfo=UTC)
    start_b = datetime(2026, 5, 1, tzinfo=UTC)
    end_b = datetime(2026, 10, 5, tzinfo=UTC)
    items = [
        _item("blood_pressure_trend", start=start_a, end=end_a),
        _item("laboratory_summary", start=start_b, end=end_b),
    ]
    period_start, period_end = compute_overview_clinical_period(items)
    assert period_start == start_b
    assert period_end == end_b


def test_appointment_rows_excluded_from_summary_period() -> None:
    measurement_start = datetime(2026, 6, 15, tzinfo=UTC)
    measurement_end = datetime(2026, 9, 1, tzinfo=UTC)
    appt_date = datetime(2025, 1, 1, tzinfo=UTC)
    items = [
        _item("blood_pressure_trend", start=measurement_start, end=measurement_end),
        _item("upcoming_follow_up", start=appt_date, end=appt_date),
    ]
    period_start, period_end = compute_overview_clinical_period(items)
    assert period_start == measurement_start
    assert period_end == measurement_end


def test_builder_period_matches_measurement_window_for_cardiac_case() -> None:
    from datetime import date
    from decimal import Decimal
    from uuid import uuid4

    from app.application.analytics.clinical_summary_builder import (
        build_deterministic_clinical_summary,
    )
    from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle
    from app.domain.entities.health_measurement import HealthMeasurement
    from app.domain.entities.patient import Patient

    as_of = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
    patient = Patient(
        owner_id=uuid4(),
        first_name="Demo",
        last_name="Patient",
        date_of_birth=date(1975, 6, 15),
        gender="female",
    )
    measurements = [
        HealthMeasurement(
            owner_id=uuid4(),
            patient_id=uuid4(),
            measured_at=datetime(2026, 6, 15, 9, 0, tzinfo=UTC),
            systolic_pressure=142,
            heart_rate=72,
        ),
        HealthMeasurement(
            owner_id=uuid4(),
            patient_id=uuid4(),
            measured_at=datetime(2026, 8, 22, 9, 0, tzinfo=UTC),
            systolic_pressure=136,
            heart_rate=74,
        ),
        HealthMeasurement(
            owner_id=uuid4(),
            patient_id=uuid4(),
            measured_at=datetime(2026, 10, 5, 9, 0, tzinfo=UTC),
            systolic_pressure=130,
            heart_rate=76,
        ),
    ]
    summary = build_deterministic_clinical_summary(
        ClinicalEvidenceBundle(patient=patient, health_measurements=measurements),
        date_from=None,
        date_to=None,
        generated_at=as_of,
    )
    assert summary.overview_clinical_period_start is not None
    assert summary.overview_clinical_period_end is not None
    assert summary.overview_clinical_period_start.date().isoformat() == "2026-06-15"
    assert summary.overview_clinical_period_end.date().isoformat() == "2026-10-05"

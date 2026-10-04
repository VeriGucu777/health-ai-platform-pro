"""Unit tests for clinical timeline mapping and derived trend rules."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.application.analytics.clinical_timeline_rules import (
    derived_trend_events,
    events_from_appointment,
    events_from_medical_record,
)
from app.domain.entities.appointment import Appointment
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord


def _measurement(
    *,
    measured_at: datetime,
    blood_glucose: Decimal | None = None,
    glucose_context: str | None = None,
) -> HealthMeasurement:
    return HealthMeasurement(
        owner_id=uuid4(),
        patient_id=uuid4(),
        measured_at=measured_at,
        blood_glucose=blood_glucose,
        glucose_context=glucose_context,
    )


def test_lab_result_record_maps_to_lab_event_type() -> None:
    record = MedicalRecord(
        owner_id=uuid4(),
        patient_id=uuid4(),
        record_date=datetime(2026, 3, 1, tzinfo=UTC),
        record_type="lab_result",
        title="Lipid panel",
        diagnosis="LDL 142 mg/dL; HDL 48 mg/dL",
    )
    events = events_from_medical_record(record)
    assert len(events) == 1
    assert events[0].event_type == "medical_record_lab_result"


def test_imaging_record_maps_to_imaging_event_type() -> None:
    record = MedicalRecord(
        owner_id=uuid4(),
        patient_id=uuid4(),
        record_date=datetime(2026, 3, 1, tzinfo=UTC),
        record_type="imaging",
        title="Echocardiography summary",
        diagnosis="LVEF 55%",
    )
    events = events_from_medical_record(record)
    assert events[0].event_type == "medical_record_imaging_report"


def test_mixed_fasting_and_post_meal_glucose_does_not_emit_increasing_trend() -> None:
    patient_id = uuid4()
    measurements = [
        _measurement(
            measured_at=datetime(2026, 4, 20, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("104"),
            glucose_context="fasting",
        ),
        _measurement(
            measured_at=datetime(2026, 5, 18, 9, 0, tzinfo=UTC),
            blood_glucose=Decimal("118"),
            glucose_context="post_meal",
        ),
    ]
    events = derived_trend_events(
        measurements,
        patient_id=patient_id,
        as_of=datetime(2026, 10, 3, 12, 0, tzinfo=UTC),
    )
    assert not any(event.event_type == "measurement_trend_derived" for event in events)
    assert any(
        event.event_type == "measurement_trend_insufficient_comparable" for event in events
    )


def test_three_fasting_increasing_emits_warning_trend() -> None:
    patient_id = uuid4()
    measurements = [
        _measurement(
            measured_at=datetime(2026, 1, 1, tzinfo=UTC),
            blood_glucose=Decimal("100"),
            glucose_context="fasting",
        ),
        _measurement(
            measured_at=datetime(2026, 2, 1, tzinfo=UTC),
            blood_glucose=Decimal("110"),
            glucose_context="fasting",
        ),
        _measurement(
            measured_at=datetime(2026, 3, 1, tzinfo=UTC),
            blood_glucose=Decimal("125"),
            glucose_context="fasting",
        ),
    ]
    events = derived_trend_events(
        measurements,
        patient_id=patient_id,
        as_of=datetime(2026, 10, 3, tzinfo=UTC),
    )
    assert any(event.event_type == "measurement_trend_derived" for event in events)


def test_two_comparable_fasting_points_do_not_emit_directional_trend() -> None:
    patient_id = uuid4()
    measurements = [
        _measurement(
            measured_at=datetime(2026, 1, 1, tzinfo=UTC),
            blood_glucose=Decimal("100"),
            glucose_context="fasting",
        ),
        _measurement(
            measured_at=datetime(2026, 2, 1, tzinfo=UTC),
            blood_glucose=Decimal("130"),
            glucose_context="fasting",
        ),
    ]
    events = derived_trend_events(
        measurements,
        patient_id=patient_id,
        as_of=datetime(2026, 10, 3, tzinfo=UTC),
    )
    assert not any(event.event_type == "measurement_trend_derived" for event in events)


def test_completed_appointment_does_not_emit_overdue() -> None:
    appointment = Appointment(
        owner_id=uuid4(),
        patient_id=uuid4(),
        appointment_date=datetime(2025, 1, 1, tzinfo=UTC),
        appointment_type="follow_up",
        status="completed",
    )
    events = events_from_appointment(
        appointment,
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert not any(event.event_type == "appointment_overdue" for event in events)


def test_cancelled_appointment_does_not_emit_overdue() -> None:
    appointment = Appointment(
        owner_id=uuid4(),
        patient_id=uuid4(),
        appointment_date=datetime(2025, 1, 1, tzinfo=UTC),
        appointment_type="follow_up",
        status="cancelled",
    )
    events = events_from_appointment(
        appointment,
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert not any(event.event_type == "appointment_overdue" for event in events)

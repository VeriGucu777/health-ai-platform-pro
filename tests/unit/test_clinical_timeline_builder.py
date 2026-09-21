"""Unit tests for clinical timeline builder helpers."""

from datetime import UTC, datetime
from uuid import uuid4

from app.application.analytics.clinical_timeline_builder import (
    apply_event_limit,
    filter_events_by_window,
    merge_and_sort_timeline_events,
)
from app.application.analytics.clinical_timeline_rules import (
    events_from_appointment,
    events_from_medical_record,
)
from app.domain.entities.clinical_timeline import ClinicalTimelineEvent, ClinicalTimelineSource
from app.domain.entities.medical_record import MedicalRecord


def _event(at: datetime, headline: str) -> ClinicalTimelineEvent:
    return ClinicalTimelineEvent(
        occurred_at=at,
        event_type="test",
        headline=headline,
        detail="detail",
        source=ClinicalTimelineSource(kind="derived", id=uuid4()),
    )


def test_merge_and_sort_newest_first() -> None:
    older = _event(datetime(2024, 1, 1, tzinfo=UTC), "older")
    newer = _event(datetime(2026, 1, 1, tzinfo=UTC), "newer")
    merged = merge_and_sort_timeline_events([[older], [newer]])
    assert [event.headline for event in merged] == ["newer", "older"]


def test_apply_event_limit_truncates() -> None:
    events = [_event(datetime(2026, 1, day, tzinfo=UTC), f"e{day}") for day in range(1, 6)]
    limited, truncated = apply_event_limit(events, 3)
    assert truncated is True
    assert len(limited) == 3


def test_filter_events_by_window() -> None:
    events = [
        _event(datetime(2025, 1, 1, tzinfo=UTC), "inside"),
        _event(datetime(2020, 1, 1, tzinfo=UTC), "outside"),
    ]
    filtered = filter_events_by_window(
        events,
        date_from=datetime(2024, 1, 1, tzinfo=UTC),
        date_to=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert len(filtered) == 1
    assert filtered[0].headline == "inside"


def test_medical_record_diagnosis_event() -> None:
    record = MedicalRecord(
        owner_id=uuid4(),
        patient_id=uuid4(),
        record_date=datetime(2024, 6, 1, tzinfo=UTC),
        record_type="visit",
        title="Checkup",
        diagnosis="Hypertension",
    )
    events = events_from_medical_record(record)
    assert any(event.event_type == "medical_record_diagnosis" for event in events)


def test_appointment_overdue_derived_event() -> None:
    from app.domain.entities.appointment import Appointment

    appointment = Appointment(
        owner_id=uuid4(),
        patient_id=uuid4(),
        appointment_date=datetime(2025, 1, 1, tzinfo=UTC),
        appointment_type="follow_up",
        status="scheduled",
    )
    events = events_from_appointment(
        appointment,
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert any(event.event_type == "appointment_overdue" for event in events)
    overdue = next(event for event in events if event.event_type == "appointment_overdue")
    assert overdue.source.kind == "derived"

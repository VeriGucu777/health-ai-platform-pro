"""Unit tests for follow-up overdue rules."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.application.analytics.follow_up_status import is_follow_up_overdue
from app.domain.entities.appointment import Appointment

_OWNER = UUID("00000000-0000-4000-8000-000000000001")
_PATIENT = UUID("00000000-0000-4000-8000-000000000002")


def _appointment(**overrides) -> Appointment:
    base = {
        "owner_id": overrides.pop("owner_id", _OWNER),
        "patient_id": overrides.pop("patient_id", _PATIENT),
        "appointment_date": datetime(2026, 1, 1, tzinfo=UTC),
        "appointment_type": "follow_up",
        "status": "scheduled",
        "notes": None,
    }
    base.update(overrides)
    return Appointment(**base)


def test_overdue_when_scheduled_and_past() -> None:
    appointment = _appointment(
        appointment_date=datetime(2026, 1, 1, tzinfo=UTC),
        status="scheduled",
    )
    assert is_follow_up_overdue(appointment, as_of=datetime(2026, 6, 1, tzinfo=UTC)) is True


def test_not_overdue_when_completed() -> None:
    appointment = _appointment(
        appointment_date=datetime(2026, 1, 1, tzinfo=UTC),
        status="completed",
    )
    assert is_follow_up_overdue(appointment, as_of=datetime(2026, 6, 1, tzinfo=UTC)) is False


def test_not_overdue_when_future_scheduled() -> None:
    as_of = datetime(2026, 6, 1, tzinfo=UTC)
    appointment = _appointment(
        appointment_date=as_of + timedelta(days=7),
        status="scheduled",
    )
    assert is_follow_up_overdue(appointment, as_of=as_of) is False

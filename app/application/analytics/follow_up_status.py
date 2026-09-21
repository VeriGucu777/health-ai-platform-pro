"""Follow-up and appointment overdue rules for the clinical timeline."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.appointment import Appointment


def is_follow_up_overdue(appointment: Appointment, *, as_of: datetime) -> bool:
    """Return True when a scheduled appointment date is in the past."""
    normalized_as_of = _ensure_utc(as_of)
    appointment_date = _ensure_utc(appointment.appointment_date)
    status = appointment.status.strip().lower()
    return status == "scheduled" and appointment_date < normalized_as_of


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

"""Entity factories for PostgreSQL integration tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import count
from uuid import UUID, uuid4

from app.domain.entities.appointment import Appointment
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole

_sequence = count(1)


def _next_suffix() -> int:
    return next(_sequence)


def make_user(**overrides) -> User:
    """Build a user entity with unique email."""
    suffix = _next_suffix()
    defaults = {
        "email": f"integration-user-{suffix}@example.test",
        "hashed_password": "$2b$12$integration.test.hash.value",
        "first_name": "Integration",
        "last_name": f"User{suffix}",
        "role": UserRole.PATIENT,
    }
    defaults.update(overrides)
    return User(**defaults)


def make_patient(owner_id: UUID, **overrides) -> Patient:
    """Build a patient entity for the given owner."""
    suffix = _next_suffix()
    defaults = {
        "owner_id": owner_id,
        "first_name": "Pat",
        "last_name": f"Example{suffix}",
        "date_of_birth": date(1990, 1, 15),
        "gender": "female",
        "phone": "+15550001111",
        "notes": "integration test patient",
    }
    defaults.update(overrides)
    return Patient(**defaults)


def make_appointment(owner_id: UUID, patient_id: UUID, **overrides) -> Appointment:
    """Build an appointment entity."""
    defaults = {
        "owner_id": owner_id,
        "patient_id": patient_id,
        "appointment_date": datetime.now(UTC) + timedelta(days=3),
        "appointment_type": "checkup",
        "status": "scheduled",
        "notes": "integration test appointment",
    }
    defaults.update(overrides)
    return Appointment(**defaults)


def make_medical_record(owner_id: UUID, patient_id: UUID, **overrides) -> MedicalRecord:
    """Build a medical record entity."""
    suffix = _next_suffix()
    defaults = {
        "owner_id": owner_id,
        "patient_id": patient_id,
        "record_date": datetime.now(UTC),
        "record_type": "visit",
        "title": f"Integration Record {suffix}",
        "description": "Created by integration tests",
        "diagnosis": "N/A",
    }
    defaults.update(overrides)
    return MedicalRecord(**defaults)


def make_health_measurement(owner_id: UUID, patient_id: UUID, **overrides) -> HealthMeasurement:
    """Build a health measurement entity."""
    defaults = {
        "owner_id": owner_id,
        "patient_id": patient_id,
        "measured_at": datetime.now(UTC),
        "blood_glucose": Decimal("110.5"),
        "glucose_context": "fasting",
        "systolic_pressure": 120,
        "diastolic_pressure": 80,
        "heart_rate": 72,
    }
    defaults.update(overrides)
    return HealthMeasurement(**defaults)


def random_owner_id() -> UUID:
    """Return a UUID that is unlikely to exist in the database."""
    return uuid4()

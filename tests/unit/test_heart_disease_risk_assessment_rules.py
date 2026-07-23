"""Unit tests for heart disease risk feature extraction helpers."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.application.analytics.heart_disease_risk_assessment import (
    build_feature_vector,
    detect_missing_inputs,
    has_minimum_required_inputs,
)
from app.application.analytics.risk_assessment_common import ResolvedAssessmentWindow
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient


def _patient(*, date_of_birth: date = date(1990, 5, 15)) -> Patient:
    return Patient(
        owner_id=uuid4(),
        first_name="John",
        last_name="Doe",
        date_of_birth=date_of_birth,
        gender="male",
    )


def _measurement(
    *,
    measured_at: datetime,
    systolic_pressure: int | None = None,
    diastolic_pressure: int | None = None,
    heart_rate: int | None = None,
) -> HealthMeasurement:
    return HealthMeasurement(
        owner_id=uuid4(),
        patient_id=uuid4(),
        measured_at=measured_at,
        systolic_pressure=systolic_pressure,
        diastolic_pressure=diastolic_pressure,
        heart_rate=heart_rate,
    )


def _window() -> ResolvedAssessmentWindow:
    return ResolvedAssessmentWindow(
        date_from=datetime(2026, 8, 1, tzinfo=UTC),
        date_to=datetime(2026, 8, 31, 23, 59, 59, tzinfo=UTC),
    )


def test_build_feature_vector_extracts_blood_pressure_and_history_types() -> None:
    window = _window()
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            systolic_pressure=118,
            diastolic_pressure=76,
            heart_rate=72,
        )
    ]
    medical_records = [
        MedicalRecord(
            owner_id=uuid4(),
            patient_id=uuid4(),
            record_date=datetime(2026, 8, 9, 10, 0, tzinfo=UTC),
            record_type="cardiovascular_history",
            title="Cardiology intake",
        )
    ]

    features = build_feature_vector(_patient(), measurements, medical_records, window)

    assert features.average_systolic_pressure == Decimal("118")
    assert features.average_diastolic_pressure == Decimal("76")
    assert features.average_heart_rate == Decimal("72")
    assert features.cardiovascular_history_record_types == ("cardiovascular_history",)


def test_detect_missing_inputs_flags_required_blood_pressure() -> None:
    features = build_feature_vector(_patient(), [], [], _window())
    missing = detect_missing_inputs(features)

    assert any(item.input == "systolic_blood_pressure" for item in missing)
    assert any(item.input == "diastolic_blood_pressure" for item in missing)
    assert any(item.input == "cholesterol" for item in missing)
    assert has_minimum_required_inputs(features) is False

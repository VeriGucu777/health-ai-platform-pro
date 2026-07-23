"""Unit tests for diabetes risk feature extraction helpers."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.application.analytics.diabetes_risk_assessment import (
    ResolvedAssessmentWindow,
    build_feature_vector,
    detect_missing_inputs,
    extract_structured_medical_record_types,
    has_minimum_required_inputs,
)
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
    blood_glucose: Decimal | None = None,
    glucose_context: str | None = None,
    systolic_pressure: int | None = None,
) -> HealthMeasurement:
    return HealthMeasurement(
        owner_id=uuid4(),
        patient_id=uuid4(),
        measured_at=measured_at,
        blood_glucose=blood_glucose,
        glucose_context=glucose_context,
        systolic_pressure=systolic_pressure,
        diastolic_pressure=80 if systolic_pressure is not None else None,
    )


def _window() -> ResolvedAssessmentWindow:
    return ResolvedAssessmentWindow(
        date_from=datetime(2026, 8, 1, tzinfo=UTC),
        date_to=datetime(2026, 8, 31, 23, 59, 59, tzinfo=UTC),
    )


def test_build_feature_vector_uses_fasting_glucose_and_structured_record_types() -> None:
    window = _window()
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("95"),
            glucose_context="fasting",
            systolic_pressure=118,
        )
    ]
    medical_records = [
        MedicalRecord(
            owner_id=uuid4(),
            patient_id=uuid4(),
            record_date=datetime(2026, 8, 9, 10, 0, tzinfo=UTC),
            record_type="lab_result",
            title="Glucose Panel",
        )
    ]

    features = build_feature_vector(_patient(), measurements, medical_records, window)

    assert features.latest_fasting_glucose == Decimal("95")
    assert features.average_systolic_pressure == Decimal("118")
    assert features.structured_medical_record_types == ("lab_result",)


def test_detect_missing_inputs_includes_glucose_and_height() -> None:
    features = build_feature_vector(_patient(), [], [], _window())
    missing = detect_missing_inputs(features)

    assert any(item.input == "blood_glucose" for item in missing)
    assert any(item.input == "height_cm" for item in missing)
    assert has_minimum_required_inputs(features) is False


def test_extract_structured_medical_record_types_ignores_unstructured_types() -> None:
    records = [
        MedicalRecord(
            owner_id=uuid4(),
            patient_id=uuid4(),
            record_date=datetime(2026, 8, 1, tzinfo=UTC),
            record_type="custom_note",
            title="Note",
            diagnosis="Should not be parsed",
        )
    ]

    assert extract_structured_medical_record_types(records) == ()

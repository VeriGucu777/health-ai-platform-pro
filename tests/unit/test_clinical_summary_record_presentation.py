"""Unit tests for clinical summary record sanitization and lipid parsing."""

from app.application.analytics.clinical_summary_record_presentation import (
    extract_hba1c_value,
    extract_lipid_panel_values,
    is_documented_cardiac_monitoring_care_plan,
    is_documented_diabetes_monitoring_care_plan,
    is_documented_stroke_secondary_prevention_plan,
    is_stroke_neurology_follow_up_record,
    sanitize_clinical_summary_text,
)
from app.domain.entities.medical_record import MedicalRecord
from uuid import uuid4
from datetime import UTC, datetime


def test_sanitize_removes_synthetic_and_fictional_demo_phrases() -> None:
    raw = (
        "Synthetic lipid panel (demo): LDL 156 mg/dL; HDL 42 mg/dL; "
        "triglycerides 190 mg/dL. Fictional demo values for decision-support review only."
    )
    cleaned = sanitize_clinical_summary_text(raw)
    assert "Synthetic" not in cleaned
    assert "Fictional" not in cleaned
    assert "decision-support review only" not in cleaned.lower()
    assert "156" in cleaned
    assert "190" in cleaned


def test_detects_stroke_neurology_follow_up_record() -> None:
    record = MedicalRecord(
        owner_id=uuid4(),
        patient_id=uuid4(),
        record_date=datetime(2026, 5, 1, tzinfo=UTC),
        record_type="visit",
        title="Neurology follow-up",
        diagnosis="Residual mild hemiparesis after stroke.",
    )
    assert is_stroke_neurology_follow_up_record(record) is True


def test_detects_stroke_secondary_prevention_medication_plan() -> None:
    record = MedicalRecord(
        owner_id=uuid4(),
        patient_id=uuid4(),
        record_date=datetime(2026, 5, 1, tzinfo=UTC),
        record_type="visit",
        title="Stroke follow-up",
        medications="Antiplatelet and statin therapy per recorded plan",
    )
    assert is_documented_stroke_secondary_prevention_plan(record) is True


def test_detects_diabetes_monitoring_care_plan_text() -> None:
    raw = (
        "Continue home glucose logging, quarterly HbA1c, and lifestyle counseling "
        "(synthetic demo plan)."
    )
    assert is_documented_diabetes_monitoring_care_plan(raw) is True


def test_detects_a2_cardiac_monitoring_care_plan_text() -> None:
    raw = (
        "Blood pressure targets, lipid recheck in 3 months, and activity guidance "
        "(synthetic demo plan)."
    )
    assert is_documented_cardiac_monitoring_care_plan(raw) is True


def test_extract_hba1c_value_from_lab_text() -> None:
    assert extract_hba1c_value("HbA1c 7.2%; LDL 142 mg/dL") == "7.2"
    assert extract_hba1c_value("metabolic panel; hba1c: 7,4%") == "7.4"
    assert extract_hba1c_value("LDL 140 mg/dL only") is None


def test_extract_lipid_panel_values_from_demo_text() -> None:
    raw = "Synthetic lipid panel (demo): LDL 156 mg/dL; HDL 42 mg/dL; triglycerides 190 mg/dL."
    values = extract_lipid_panel_values(raw)
    assert values is not None
    assert values.ldl == "156"
    assert values.hdl == "42"
    assert values.triglycerides == "190"

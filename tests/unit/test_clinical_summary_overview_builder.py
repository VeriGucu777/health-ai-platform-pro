"""Unit tests for deterministic clinical summary overview bullets."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.application.analytics.clinical_summary_overview_builder import (
    build_clinical_summary_overview_items,
)
from app.application.analytics.clinical_summary_overview_period import (
    compute_overview_clinical_period,
)
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle
from app.domain.entities.appointment import Appointment
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.risk.enums import RULE_BASED_MODEL_KIND, RiskAssessmentType


def _patient() -> Patient:
    return Patient(
        owner_id=uuid4(),
        first_name="Demo",
        last_name="Patient",
        date_of_birth=date(1975, 6, 15),
        gender="female",
    )


def _bundle(**kwargs: object) -> ClinicalEvidenceBundle:
    return ClinicalEvidenceBundle(patient=_patient(), **kwargs)  # type: ignore[arg-type]


def _measurement(
    *,
    measured_at: datetime,
    blood_glucose: Decimal | None = None,
    glucose_context: str | None = None,
    systolic_pressure: int | None = None,
    diastolic_pressure: int | None = None,
    heart_rate: int | None = None,
    is_active: bool = True,
) -> HealthMeasurement:
    return HealthMeasurement(
        owner_id=uuid4(),
        patient_id=uuid4(),
        measured_at=measured_at,
        blood_glucose=blood_glucose,
        glucose_context=glucose_context,
        systolic_pressure=systolic_pressure,
        diastolic_pressure=diastolic_pressure,
        heart_rate=heart_rate,
        is_active=is_active,
    )


def _record(**kwargs: object) -> MedicalRecord:
    defaults = {
        "owner_id": uuid4(),
        "patient_id": uuid4(),
        "record_date": datetime(2026, 5, 1, tzinfo=UTC),
        "record_type": "visit",
        "title": "Visit",
    }
    defaults.update(kwargs)
    return MedicalRecord(**defaults)  # type: ignore[arg-type]


def test_diabetes_overview_includes_glucose_lab_and_follow_up() -> None:
    as_of = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 1, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("108"),
            glucose_context="fasting",
            systolic_pressure=128,
            diastolic_pressure=82,
        ),
        _measurement(
            measured_at=datetime(2026, 8, 15, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("112"),
            glucose_context="fasting",
            systolic_pressure=130,
            diastolic_pressure=84,
        ),
        _measurement(
            measured_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("118"),
            glucose_context="fasting",
            systolic_pressure=132,
            diastolic_pressure=86,
        ),
        _measurement(
            measured_at=datetime(2026, 9, 10, 13, 0, tzinfo=UTC),
            blood_glucose=Decimal("165"),
            glucose_context="post_meal",
        ),
        _measurement(
            measured_at=datetime(2026, 9, 20, 13, 0, tzinfo=UTC),
            blood_glucose=Decimal("172"),
            glucose_context="post_meal",
        ),
    ]
    records = [
        _record(
            record_type="lab_result",
            title="Metabolic laboratory panel",
            diagnosis="HbA1c 7.2%; LDL 142 mg/dL",
        ),
        _record(
            record_type="visit",
            title="Diabetes follow-up",
            medications="Metformin 1000 mg twice daily",
        ),
    ]
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=as_of + timedelta(days=14),
            appointment_type="Diabetes follow-up",
            status="scheduled",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(
            health_measurements=measurements,
            medical_records=records,
            appointments=appointments,
        ),
        as_of=as_of,
    )
    keys = [item.key for item in items]
    assert keys == [
        "fasting_glucose_trend",
        "post_meal_glucose_trend",
        "laboratory_summary",
        "blood_pressure_trend",
        "medication_treatment_follow_up",
        "upcoming_follow_up",
    ]
    fasting = next(item for item in items if item.key == "fasting_glucose_trend")
    assert fasting.trend_status == "increasing"
    assert fasting.source_count == 3
    assert fasting.message_key == "trend_hybrid_increasing"

    lab = next(item for item in items if item.key == "laboratory_summary")
    assert lab.message_key == "hba1c_summary"
    assert lab.message_params["value"] == "7.2"

    med = next(item for item in items if item.key == "medication_treatment_follow_up")
    assert med.message_key == "diabetes_medication_documented"


def test_diabetes_treatment_plan_uses_localized_message_key_not_raw_english() -> None:
    as_of = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    records = [
        _record(
            record_type="lab_result",
            title="Metabolic laboratory panel",
            diagnosis="HbA1c 7.4%",
        ),
        _record(
            record_date=datetime(2026, 9, 15, tzinfo=UTC),
            record_type="visit",
            title="Diabetes follow-up",
            treatment=(
                "Continue home glucose logging, quarterly HbA1c, and lifestyle counseling"
            ),
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(
            health_measurements=[
                _measurement(
                    measured_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
                    blood_glucose=Decimal("112"),
                    glucose_context="fasting",
                ),
            ],
            medical_records=records,
        ),
        as_of=as_of,
    )
    med = next(item for item in items if item.key == "medication_treatment_follow_up")
    assert med.message_key == "diabetes_follow_up_plan_documented"
    assert "Continue home glucose logging" not in med.message


def test_diabetes_focus_overdue_follow_up_is_sixth_item() -> None:
    as_of = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 1, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("108"),
            glucose_context="fasting",
            systolic_pressure=128,
        ),
        _measurement(
            measured_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("112"),
            glucose_context="fasting",
            systolic_pressure=130,
        ),
    ]
    records = [
        _record(
            record_type="lab_result",
            title="Metabolic laboratory panel",
            diagnosis="HbA1c 7.4%",
        ),
        _record(
            record_type="visit",
            title="Diabetes follow-up",
            medications="Metformin 1000 mg twice daily",
        ),
    ]
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=datetime(2026, 8, 10, 14, 0, tzinfo=UTC),
            appointment_type="Diabetes follow-up",
            status="scheduled",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(
            health_measurements=measurements,
            medical_records=records,
            appointments=appointments,
        ),
        as_of=as_of,
    )
    assert items[-1].key == "overdue_follow_up"
    assert items[-1].message_key == "overdue_follow_up_date"


def test_cardiac_focus_never_includes_glucose_even_without_appointments() -> None:
    as_of = datetime(2026, 10, 5, tzinfo=UTC)
    measurements = [
        _measurement(
            measured_at=datetime(2026, 9, 1, tzinfo=UTC),
            blood_glucose=Decimal("118"),
            glucose_context="fasting",
            systolic_pressure=130,
        ),
    ]
    records = [
        _record(
            record_type="lab_result",
            title="Lipid panel",
            diagnosis="LDL 156 mg/dL; HDL 42 mg/dL; triglycerides 190 mg/dL.",
        ),
        _record(record_type="imaging", title="Echocardiography summary", diagnosis="On file"),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(health_measurements=measurements, medical_records=records),
        as_of=as_of,
    )
    assert "fasting_glucose_trend" not in [item.key for item in items]
    assert "post_meal_glucose_trend" not in [item.key for item in items]


def test_cardiac_focus_orders_bp_hr_lab_imaging_medication_appointment() -> None:
    as_of = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    measurements = [
        _measurement(
            measured_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
            systolic_pressure=142,
            heart_rate=72,
            blood_glucose=Decimal("108"),
            glucose_context="fasting",
        ),
        _measurement(
            measured_at=datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
            systolic_pressure=136,
            heart_rate=74,
            blood_glucose=Decimal("112"),
            glucose_context="fasting",
        ),
        _measurement(
            measured_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            systolic_pressure=130,
            heart_rate=76,
        ),
    ]
    records = [
        _record(
            record_type="lab_result",
            title="Lipid panel (demo)",
            diagnosis=(
                "Synthetic lipid panel (demo): LDL 156 mg/dL; HDL 42 mg/dL; "
                "triglycerides 190 mg/dL."
            ),
            description="Fictional demo values for decision-support review only.",
        ),
        _record(
            record_type="imaging",
            title="Echocardiography summary (demo)",
            diagnosis=(
                "Synthetic echocardiography report summary (demo): documented for chart "
                "review; no image file or automated analysis."
            ),
            description="Fictional demo imaging narrative for decision-support review only.",
        ),
        _record(
            record_date=datetime(2026, 8, 10, tzinfo=UTC),
            record_type="visit",
            title="Medication adjustment (demo)",
            medications=(
                "Antihypertensive and statin therapy reviewed; dose adjustment noted "
                "(synthetic demo text only)."
            ),
        ),
        _record(
            record_date=datetime(2026, 9, 20, tzinfo=UTC),
            record_type="visit",
            title="Cardiac follow-up plan (demo)",
            treatment=(
                "Blood pressure targets, lipid recheck in 3 months, and activity guidance "
                "(synthetic demo plan)."
            ),
        ),
    ]
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=as_of + timedelta(days=12),
            appointment_type="Cardiac follow-up",
            status="scheduled",
        ),
    ]
    risk_history = [
        RiskAssessmentHistory(
            patient_id=uuid4(),
            assessment_type=RiskAssessmentType.HEART_DISEASE,
            assessment_status="complete",
            risk_level="moderate",
            score=58.0,
            probability=0.4,
            model_kind=RULE_BASED_MODEL_KIND,
            model_version="heart_rule_based_v1",
            evaluated_by_user_id=uuid4(),
            evaluated_at=datetime(2026, 9, 15, tzinfo=UTC),
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(
            health_measurements=measurements,
            medical_records=records,
            appointments=appointments,
            risk_assessment_history=risk_history,
        ),
        as_of=as_of,
    )
    keys = [item.key for item in items]
    assert keys == [
        "blood_pressure_trend",
        "heart_rate_trend",
        "laboratory_summary",
        "imaging_summary",
        "medication_treatment_follow_up",
        "upcoming_follow_up",
    ]
    assert "fasting_glucose_trend" not in keys

    lab = next(item for item in items if item.key == "laboratory_summary")
    assert lab.message_key == "lipid_panel_with_triglycerides"
    assert lab.message_params["ldl"] == "156"
    assert lab.message_params["hdl"] == "42"
    assert lab.message_params["triglycerides"] == "190"
    assert lab.message_params["record_date"] == "2026-05-01"
    assert "Synthetic" not in lab.message
    assert "Fictional" not in lab.message

    imaging = next(item for item in items if item.key == "imaging_summary")
    assert imaging.message_key == "echocardiography_on_file"
    assert "Synthetic" not in imaging.message

    med = next(item for item in items if item.key == "medication_treatment_follow_up")
    assert med.message_key == "cardiac_care_plan_documented"
    assert "Blood pressure targets" not in med.message_params.get("detail", med.message)

    bp = next(item for item in items if item.key == "blood_pressure_trend")
    assert bp.trend_status == "decreasing"
    assert bp.source_count == 3
    assert bp.message_key == "trend_hybrid_decreasing"
    assert bp.message_params["window_start"] == "2026-07-01"
    assert bp.message_params["window_end"] == "2026-09-01"

    period_start, period_end = compute_overview_clinical_period(items)
    assert period_start is not None
    assert period_end is not None
    assert period_start.date().isoformat() == "2026-05-01"
    assert period_end.date().isoformat() == "2026-09-20"


def test_past_scheduled_appointment_produces_overdue_follow_up() -> None:
    as_of = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=datetime(2026, 8, 10, 14, 0, tzinfo=UTC),
            appointment_type="follow_up",
            status="scheduled",
        ),
    ]
    records = [
        _record(
            record_type="lab_result",
            title="Lipid panel",
            diagnosis="LDL 156 mg/dL; HDL 42 mg/dL; triglycerides 190 mg/dL.",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(appointments=appointments, medical_records=records),
        as_of=as_of,
    )
    overdue = next(item for item in items if item.key == "overdue_follow_up")
    assert overdue.message_key == "overdue_follow_up_date"
    assert overdue.message_params["date"] == "2026-08-10"


def test_past_completed_appointment_does_not_produce_overdue() -> None:
    as_of = datetime(2026, 10, 5, tzinfo=UTC)
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=datetime(2026, 8, 10, tzinfo=UTC),
            appointment_type="follow_up",
            status="completed",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(appointments=appointments),
        as_of=as_of,
    )
    assert not any(item.key == "overdue_follow_up" for item in items)


def test_past_cancelled_appointment_does_not_produce_overdue() -> None:
    as_of = datetime(2026, 10, 5, tzinfo=UTC)
    for status in ("cancelled", "canceled"):
        appointments = [
            Appointment(
                owner_id=uuid4(),
                patient_id=uuid4(),
                appointment_date=datetime(2026, 8, 10, tzinfo=UTC),
                appointment_type="follow_up",
                status=status,
            ),
        ]
        items = build_clinical_summary_overview_items(
            _bundle(appointments=appointments),
            as_of=as_of,
        )
        assert not any(item.key == "overdue_follow_up" for item in items)


def test_future_scheduled_prefers_upcoming_over_overdue() -> None:
    as_of = datetime(2026, 10, 5, tzinfo=UTC)
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=datetime(2026, 8, 10, tzinfo=UTC),
            appointment_type="follow_up",
            status="scheduled",
        ),
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=datetime(2026, 11, 15, tzinfo=UTC),
            appointment_type="follow_up",
            status="scheduled",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(appointments=appointments),
        as_of=as_of,
    )
    follow_up_items = [item for item in items if item.key in {"upcoming_follow_up", "overdue_follow_up"}]
    assert len(follow_up_items) == 1
    assert follow_up_items[0].key == "upcoming_follow_up"


def test_cardiac_overdue_excludes_glucose_from_first_six() -> None:
    as_of = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
    measurements = [
        _measurement(
            measured_at=datetime(2026, 9, 1, tzinfo=UTC),
            blood_glucose=Decimal("104"),
            glucose_context="fasting",
            systolic_pressure=130,
        ),
    ]
    records = [
        _record(
            record_type="lab_result",
            title="Lipid panel",
            diagnosis="LDL 156 mg/dL; HDL 42 mg/dL; triglycerides 190 mg/dL.",
        ),
        _record(record_type="imaging", title="Echocardiography summary", diagnosis="On file"),
    ]
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=datetime(2026, 8, 10, 14, 0, tzinfo=UTC),
            appointment_type="follow_up",
            status="scheduled",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(
            health_measurements=measurements,
            medical_records=records,
            appointments=appointments,
        ),
        as_of=as_of,
    )
    keys = [item.key for item in items]
    assert keys[-1] == "overdue_follow_up"
    assert "fasting_glucose_trend" not in keys


def test_cardiac_no_appointment_does_not_force_glucose_filler() -> None:
    as_of = datetime(2026, 10, 5, tzinfo=UTC)
    measurements = [
        _measurement(
            measured_at=datetime(2026, 9, 1, tzinfo=UTC),
            blood_glucose=Decimal("104"),
            glucose_context="fasting",
            systolic_pressure=130,
        ),
    ]
    records = [
        _record(
            record_type="lab_result",
            title="Lipid panel",
            diagnosis="LDL 156 mg/dL; HDL 42 mg/dL; triglycerides 190 mg/dL.",
        ),
        _record(record_type="imaging", title="Echocardiography summary", diagnosis="On file"),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(health_measurements=measurements, medical_records=records),
        as_of=as_of,
    )
    assert "fasting_glucose_trend" not in [item.key for item in items]
    assert len(items) <= 5


def test_cardiac_excludes_glucose_when_scheduled_appointment_exists() -> None:
    as_of = datetime(2026, 10, 1, tzinfo=UTC)
    measurements = [
        _measurement(
            measured_at=datetime(2026, 9, 1, tzinfo=UTC),
            systolic_pressure=130,
            blood_glucose=Decimal("110"),
            glucose_context="fasting",
        ),
    ]
    records = [
        _record(
            record_type="lab_result",
            title="Lipid panel",
            diagnosis="LDL 156 mg/dL; HDL 42 mg/dL; triglycerides 190 mg/dL.",
        ),
    ]
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=as_of + timedelta(days=14),
            appointment_type="Cardiac follow-up",
            status="scheduled",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(
            health_measurements=measurements,
            medical_records=records,
            appointments=appointments,
        ),
        as_of=as_of,
    )
    keys = [item.key for item in items]
    assert "upcoming_follow_up" in keys
    assert "fasting_glucose_trend" not in keys


def test_completed_appointment_is_not_upcoming_follow_up() -> None:
    as_of = datetime(2026, 10, 1, tzinfo=UTC)
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=as_of + timedelta(days=5),
            appointment_type="Cardiac follow-up",
            status="completed",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(appointments=appointments),
        as_of=as_of,
    )
    assert not any(item.key == "upcoming_follow_up" for item in items)


def test_cardiac_heart_rate_two_measurements_use_insufficient_trend_copy() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 1, tzinfo=UTC),
            systolic_pressure=130,
            heart_rate=72,
        ),
        _measurement(
            measured_at=datetime(2026, 9, 1, tzinfo=UTC),
            systolic_pressure=128,
            heart_rate=74,
        ),
    ]
    records = [
        _record(
            record_type="lab_result",
            title="Lipid panel",
            diagnosis="LDL 156 mg/dL; HDL 42 mg/dL; triglycerides 190 mg/dL.",
        ),
        _record(record_type="imaging", title="Echocardiography summary", diagnosis="On file"),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(health_measurements=measurements, medical_records=records),
        as_of=datetime(2026, 10, 1, tzinfo=UTC),
    )
    hr = next(item for item in items if item.key == "heart_rate_trend")
    assert hr.message_key == "trend_hybrid_no_direction"
    assert hr.trend_status == "recorded_no_direction"
    assert hr.message_params["window_start"] == "2026-08-01"
    assert hr.message_params["window_end"] == "2026-09-01"
    assert hr.source_count == 2


def test_stroke_overview_includes_neurology_imaging_and_metabolic() -> None:
    as_of = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    measurements = [
        _measurement(
            measured_at=datetime(2026, 6, 1, 8, 0, tzinfo=UTC),
            systolic_pressure=138,
            blood_glucose=Decimal("104"),
            glucose_context="fasting",
        ),
        _measurement(
            measured_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
            systolic_pressure=142,
            blood_glucose=Decimal("108"),
            glucose_context="fasting",
        ),
    ]
    records = [
        _record(
            record_type="visit",
            title="Neurology follow-up",
            diagnosis="Residual mild hemiparesis; secondary stroke prevention plan documented.",
        ),
        _record(
            record_type="imaging",
            title="Brain imaging report summary",
            diagnosis="Chronic ischemic changes without acute infarct on summary report.",
        ),
        _record(
            record_type="visit",
            medications="Antiplatelet and statin therapy per recorded plan",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(health_measurements=measurements, medical_records=records),
        as_of=as_of,
    )
    keys = [item.key for item in items]
    assert "fasting_glucose_trend" in keys
    assert "blood_pressure_trend" in keys
    assert "clinical_visit_summary" in keys
    assert "imaging_summary" in keys
    assert "medication_treatment_follow_up" in keys


def test_insufficient_data_returns_empty_overview() -> None:
    items = build_clinical_summary_overview_items(
        _bundle(),
        as_of=datetime(2026, 10, 1, tzinfo=UTC),
    )
    assert items == []


def test_inactive_measurements_excluded_from_bundle_convention() -> None:
    """Overview builder only sees active rows supplied by evidence loading."""
    active = [
        _measurement(
            measured_at=datetime(2026, 8, 1, tzinfo=UTC),
            systolic_pressure=120,
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(health_measurements=active),
        as_of=datetime(2026, 10, 1, tzinfo=UTC),
    )
    assert len(items) == 1
    assert items[0].key == "blood_pressure_trend"
    assert items[0].source_count == 1


def test_two_point_fasting_glucose_does_not_claim_direction() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 1, tzinfo=UTC),
            blood_glucose=Decimal("100"),
            glucose_context="fasting",
        ),
        _measurement(
            measured_at=datetime(2026, 9, 1, tzinfo=UTC),
            blood_glucose=Decimal("130"),
            glucose_context="fasting",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(health_measurements=measurements),
        as_of=datetime(2026, 10, 1, tzinfo=UTC),
    )
    fasting = next(item for item in items if item.key == "fasting_glucose_trend")
    assert fasting.trend_status == "recorded_no_direction"
    assert fasting.message_key == "trend_hybrid_no_direction"
    assert "not enough data for a directional trend" in fasting.message


def test_fasting_and_post_meal_glucose_evaluated_separately() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 1, tzinfo=UTC),
            blood_glucose=Decimal("105"),
            glucose_context="fasting",
        ),
        _measurement(
            measured_at=datetime(2026, 8, 2, tzinfo=UTC),
            blood_glucose=Decimal("190"),
            glucose_context="post_meal",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(health_measurements=measurements),
        as_of=datetime(2026, 10, 1, tzinfo=UTC),
    )
    keys = [item.key for item in items]
    assert "fasting_glucose_trend" in keys
    assert "post_meal_glucose_trend" in keys


def test_scheduled_appointment_summary() -> None:
    as_of = datetime(2026, 10, 1, tzinfo=UTC)
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=as_of + timedelta(days=10),
            appointment_type="Stroke follow-up",
            status="scheduled",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(appointments=appointments),
        as_of=as_of,
    )
    assert len(items) == 1
    assert items[0].key == "upcoming_follow_up"
    assert "stroke follow-up" in items[0].message


def test_seed_markers_stripped_from_record_snippets() -> None:
    records = [
        _record(
            record_type="lab_result",
            title="Panel",
            diagnosis="HbA1c 7.0% seed:demo-enrich-a1 hidden marker",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(medical_records=records),
        as_of=datetime(2026, 10, 1, tzinfo=UTC),
    )
    assert items
    assert "seed:" not in items[0].message.lower()
    assert "7.0%" in items[0].message or items[0].message_key is not None


def test_overview_capped_at_six_items() -> None:
    as_of = datetime(2026, 10, 1, tzinfo=UTC)
    measurements = [
        _measurement(
            measured_at=datetime(2026, 6, 1, tzinfo=UTC),
            blood_glucose=Decimal("100"),
            glucose_context="fasting",
            systolic_pressure=120,
            heart_rate=70,
        ),
        _measurement(
            measured_at=datetime(2026, 7, 1, tzinfo=UTC),
            blood_glucose=Decimal("110"),
            glucose_context="fasting",
            systolic_pressure=125,
            heart_rate=72,
        ),
        _measurement(
            measured_at=datetime(2026, 8, 1, tzinfo=UTC),
            blood_glucose=Decimal("120"),
            glucose_context="fasting",
            systolic_pressure=130,
            heart_rate=74,
        ),
        _measurement(
            measured_at=datetime(2026, 8, 2, tzinfo=UTC),
            blood_glucose=Decimal("180"),
            glucose_context="post_meal",
        ),
    ]
    records = [
        _record(record_type="lab_result", title="Lab", diagnosis="LDL 140"),
        _record(record_type="imaging", title="Echo", diagnosis="Normal LV function"),
        _record(record_type="visit", diagnosis="Stable outpatient course"),
        _record(record_type="visit", medications="Aspirin 81 mg daily"),
    ]
    appointments = [
        Appointment(
            owner_id=uuid4(),
            patient_id=uuid4(),
            appointment_date=as_of + timedelta(days=5),
            appointment_type="Follow-up",
            status="scheduled",
        ),
    ]
    items = build_clinical_summary_overview_items(
        _bundle(
            health_measurements=measurements,
            medical_records=records,
            appointments=appointments,
        ),
        as_of=as_of,
    )
    assert len(items) == 6

"""Unit tests for patient health PDF builder."""

from datetime import UTC, date, datetime
from uuid import uuid4

from app.application.dtos.health_measurement_analytics import (
    HealthMeasurementSummaryDTO,
    HealthMeasurementTrendsDTO,
    MetricStatisticsDTO,
)
from app.application.dtos.health_measurement_insights import (
    HealthMeasurementInsightsDTO,
    HealthRecommendationDTO,
    MetricInsightDTO,
)
from app.application.dtos.medical_record import MedicalRecordDTO
from app.application.dtos.patient import PatientDTO
from app.application.dtos.patient_health_report import PatientHealthReportContextDTO
from app.application.reports.patient_health_pdf_builder import build_patient_health_pdf
from app.core.reference_ranges import REPORT_PDF_DISCLAIMER
from tests.support.pdf_report_helpers import assert_disclaimers_present, extract_pdf_text


def _patient(*, first_name: str = "Şahin", last_name: str = "Öğüt") -> PatientDTO:
    now = datetime(2026, 8, 1, tzinfo=UTC)
    return PatientDTO(
        id=uuid4(),
        owner_id=uuid4(),
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date(1990, 1, 1),
        gender="male",
        phone="+905551112233",
        notes="Türkçe karakter testi",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def _context(*, medical_records: list[MedicalRecordDTO] | None = None) -> PatientHealthReportContextDTO:
    now = datetime(2026, 8, 1, tzinfo=UTC)
    patient = _patient()
    patient_id = patient.id
    summary = HealthMeasurementSummaryDTO(
        patient_id=patient_id,
        metric=None,
        date_from=now,
        date_to=datetime(2026, 8, 31, tzinfo=UTC),
        total_measurement_count=0,
        overall=[
            MetricStatisticsDTO(
                metric="blood_glucose",
                measurement_count=0,
                average=None,
                minimum=None,
                maximum=None,
                trend_direction="insufficient_data",
                target_range_status="not_applicable",
            )
        ],
    )
    trends = HealthMeasurementTrendsDTO(
        patient_id=patient_id,
        metric=None,
        date_from=now,
        date_to=datetime(2026, 8, 31, tzinfo=UTC),
        period="weekly",
        total_measurement_count=0,
        overall=summary.overall,
        periods=[],
    )
    insights = HealthMeasurementInsightsDTO(
        patient_id=patient_id,
        date_from=now,
        date_to=datetime(2026, 8, 31, tzinfo=UTC),
        overall_status="info",
        insights=[
            MetricInsightDTO(
                metric="blood_glucose",
                status="insufficient_data",
                severity="info",
                latest_value=None,
                average_value=None,
                trend_direction="insufficient_data",
                message="No blood glucose measurements were recorded in the selected date range.",
            )
        ],
        alerts=[],
        recommendations=[
            HealthRecommendationDTO(
                category="monitoring",
                message="Add more health measurements over time to generate meaningful insights.",
                related_metrics=[],
            )
        ],
    )
    return PatientHealthReportContextDTO(
        patient=patient,
        date_from=now,
        date_to=datetime(2026, 8, 31, tzinfo=UTC),
        generated_at=datetime(2026, 8, 23, 12, 0, tzinfo=UTC),
        medical_records=medical_records or [],
        medical_records_total_in_range=0,
        medical_records_truncated=False,
        measurement_summary=summary,
        measurement_trends=trends,
        clinical_insights=insights,
    )


def test_build_pdf_starts_with_pdf_signature() -> None:
    pdf_bytes = build_patient_health_pdf(_context())
    assert pdf_bytes.startswith(b"%PDF")


def test_build_pdf_contains_turkish_characters() -> None:
    pdf_bytes = build_patient_health_pdf(_context())
    text = extract_pdf_text(pdf_bytes)
    assert "Şahin" in text or "Hasta Bilgileri" in text
    assert b"/Font" in pdf_bytes


def test_build_pdf_contains_mandatory_disclaimers() -> None:
    pdf_bytes = build_patient_health_pdf(_context())
    assert_disclaimers_present(pdf_bytes)


def test_build_pdf_empty_history_sections() -> None:
    pdf_bytes = build_patient_health_pdf(_context())
    text = extract_pdf_text(pdf_bytes)
    assert "Seçilen dönemde tıbbi kayıt bulunmamaktadır." in text
    assert "Add more health measurements over time" in text


def test_build_pdf_shows_medical_record_limit_notice() -> None:
    now = datetime(2026, 8, 15, tzinfo=UTC)
    records = [
        MedicalRecordDTO(
            id=uuid4(),
            owner_id=uuid4(),
            patient_id=uuid4(),
            record_date=now,
            record_type="visit",
            title=f"Record {index}",
            description=None,
            diagnosis=None,
            treatment=None,
            medications=None,
            doctor_name="Dr. Test",
            hospital_name="Hospital",
            notes=None,
            created_at=now,
            updated_at=now,
        )
        for index in range(3)
    ]
    context = _context(medical_records=records)
    context.medical_records_total_in_range = 150
    context.medical_records_truncated = True
    pdf_bytes = build_patient_health_pdf(context)
    text = extract_pdf_text(pdf_bytes)
    assert "en yeni 100 tıbbi kayıt" in text
    assert "150" in text


def test_mandatory_disclaimer_constant_present() -> None:
    assert "not a diagnosis" in REPORT_PDF_DISCLAIMER
    assert "official clinical document" in REPORT_PDF_DISCLAIMER

"""Unit tests for patient health PDF builder."""

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.analytics.health_measurement_insights import build_insights
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
from app.application.reports.pdf_fonts import PdfFontUnavailableError, validate_pdf_font_available
from app.application.reports.report_i18n import get_report_copy
from tests.support.pdf_locale_acceptance import (
    assert_english_pdf_meets_locale_acceptance,
    assert_turkish_pdf_meets_locale_acceptance,
)
from tests.support.pdf_report_helpers import (
    assert_disclaimers_present,
    assert_pdf_has_unicode_font_embedding,
    assert_turkish_content_present,
    extract_pdf_text,
)


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


def _context(
    *,
    medical_records: list[MedicalRecordDTO] | None = None,
    locale: str = "tr",
) -> PatientHealthReportContextDTO:
    now = datetime(2026, 8, 1, tzinfo=UTC)
    patient = _patient()
    patient_id = patient.id
    payload = build_insights([], locale=locale)  # type: ignore[arg-type]
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
        overall_status=str(payload["overall_status"]),
        insights=[MetricInsightDTO(**item) for item in payload["insights"]],
        alerts=[],
        recommendations=[
            HealthRecommendationDTO(**item) for item in payload["recommendations"]
        ],
    )
    copy = get_report_copy(locale)  # type: ignore[arg-type]
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
        locale=locale,  # type: ignore[arg-type]
        insights_disclaimer=copy.insights_disclaimer,
        report_disclaimer=copy.report_disclaimer,
    )


def test_build_pdf_starts_with_pdf_signature() -> None:
    pdf_bytes = build_patient_health_pdf(_context())
    assert pdf_bytes.startswith(b"%PDF")


def test_build_pdf_contains_turkish_characters() -> None:
    pdf_bytes = build_patient_health_pdf(_context(locale="tr"))
    text = extract_pdf_text(pdf_bytes)
    assert_turkish_content_present(pdf_bytes, text)
    assert "Şahin" in text
    assert "Öğüt" in text
    assert "Türkçe karakter testi" in text
    assert "Erkek" in text


def test_build_pdf_turkish_locale_acceptance() -> None:
    pdf_bytes = build_patient_health_pdf(_context(locale="tr"))
    assert_turkish_pdf_meets_locale_acceptance(extract_pdf_text(pdf_bytes))


def test_build_pdf_english_locale_acceptance() -> None:
    pdf_bytes = build_patient_health_pdf(_context(locale="en"))
    assert_english_pdf_meets_locale_acceptance(extract_pdf_text(pdf_bytes))


def test_build_pdf_turkish_unicode_font() -> None:
    pdf_bytes = build_patient_health_pdf(_context(locale="tr"))
    text = extract_pdf_text(pdf_bytes)
    assert_turkish_content_present(pdf_bytes, text)
    assert "Hasta Sağlık Raporu" in text
    assert_pdf_has_unicode_font_embedding(pdf_bytes)


def test_build_pdf_fails_when_font_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.reports import pdf_fonts

    missing_path = Path("/tmp/health-ai-platform-pro-missing-noto.ttf")

    def _missing_font_path() -> Path:
        return missing_path

    monkeypatch.setattr(pdf_fonts, "resolve_pdf_font_path", _missing_font_path)

    with pytest.raises(PdfFontUnavailableError) as exc_info:
        validate_pdf_font_available()

    assert exc_info.value.status_code == 503
    assert exc_info.value.details["expected_filename"] == "NotoSans-Regular.ttf"


def test_build_pdf_contains_mandatory_disclaimers_turkish() -> None:
    pdf_bytes = build_patient_health_pdf(_context(locale="tr"))
    assert_disclaimers_present(pdf_bytes, locale="tr")


def test_build_pdf_empty_history_sections_turkish() -> None:
    pdf_bytes = build_patient_health_pdf(_context(locale="tr"))
    text = extract_pdf_text(pdf_bytes)
    assert "Seçilen dönemde tıbbi kayıt bulunmamaktadır." in text
    assert "Anlamlı içgörüler için" in text


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
    context = _context(medical_records=records, locale="tr")
    context.medical_records_total_in_range = 150
    context.medical_records_truncated = True
    pdf_bytes = build_patient_health_pdf(context)
    text = extract_pdf_text(pdf_bytes)
    assert "en yeni 100 tıbbi kayıt" in text
    assert "150" in text


def test_mandatory_disclaimer_constant_present() -> None:
    copy = get_report_copy("en")
    assert "not a diagnosis" in copy.report_disclaimer
    assert "official clinical document" in copy.report_disclaimer
    copy_tr = get_report_copy("tr")
    assert "resmi klinik belge değildir" in copy_tr.report_disclaimer
    assert "Tanı değildir" in copy_tr.insights_disclaimer or "Tanı" in copy_tr.insights_disclaimer

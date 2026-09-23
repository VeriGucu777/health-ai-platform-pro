"""Patient health PDF report application DTOs."""

from datetime import datetime

from pydantic import Field

from app.application.dtos.base import BaseSchema
from app.application.dtos.health_measurement_analytics import (
    HealthMeasurementSummaryDTO,
    HealthMeasurementTrendsDTO,
)
from app.application.dtos.health_measurement_insights import HealthMeasurementInsightsDTO
from app.application.dtos.medical_record import MedicalRecordDTO
from app.application.dtos.patient import PatientDTO
from app.application.reports.report_i18n import ReportLocale, get_report_copy


class PatientHealthReportContextDTO(BaseSchema):
    """Aggregated context used to render a patient health PDF report."""

    patient: PatientDTO
    date_from: datetime
    date_to: datetime
    generated_at: datetime
    medical_records: list[MedicalRecordDTO]
    medical_records_total_in_range: int
    medical_records_truncated: bool
    measurement_summary: HealthMeasurementSummaryDTO
    measurement_trends: HealthMeasurementTrendsDTO
    clinical_insights: HealthMeasurementInsightsDTO
    locale: ReportLocale = "en"
    insights_disclaimer: str = Field(
        default_factory=lambda: get_report_copy("en").insights_disclaimer
    )
    report_disclaimer: str = Field(default_factory=lambda: get_report_copy("en").report_disclaimer)

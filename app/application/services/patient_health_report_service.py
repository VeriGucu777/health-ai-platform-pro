"""Patient health PDF report orchestration service."""

from datetime import UTC, datetime
from uuid import UUID

from app.application.dtos.medical_record import MedicalRecordDTO
from app.application.dtos.patient_health_report import PatientHealthReportContextDTO
from app.application.reports.patient_health_pdf_builder import build_patient_health_pdf
from app.application.services.base import BaseService
from app.application.services.health_measurement_analytics_service import (
    HealthMeasurementAnalyticsService,
)
from app.application.services.medical_record_service import MedicalRecordService
from app.application.services.patient_service import PatientService
from app.core.reference_ranges import MAX_MEDICAL_RECORDS_IN_REPORT


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class PatientHealthReportService(BaseService):
    """Generate patient health PDF reports by composing existing read-only services."""

    def __init__(
        self,
        patient_service: PatientService,
        medical_record_service: MedicalRecordService,
        analytics_service: HealthMeasurementAnalyticsService,
    ) -> None:
        self._patients = patient_service
        self._medical_records = medical_record_service
        self._analytics = analytics_service

    async def generate_pdf(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[bytes, str]:
        patient = await self._patients.get_patient(owner_id, patient_id)

        summary = await self._analytics.get_summary(
            owner_id,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        )
        trends = await self._analytics.get_trends(
            owner_id,
            patient_id=patient_id,
            period="weekly",
            date_from=date_from,
            date_to=date_to,
        )
        insights = await self._analytics.get_insights(
            owner_id,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        )

        medical_records, total_in_range, truncated = await self._load_medical_records(
            owner_id,
            patient_id=patient_id,
            date_from=summary.date_from,
            date_to=summary.date_to,
        )

        context = PatientHealthReportContextDTO(
            patient=patient,
            date_from=summary.date_from,
            date_to=summary.date_to,
            generated_at=datetime.now(UTC),
            medical_records=medical_records,
            medical_records_total_in_range=total_in_range,
            medical_records_truncated=truncated,
            measurement_summary=summary,
            measurement_trends=trends,
            clinical_insights=insights,
        )
        filename = f"patient-health-report-{patient_id}.pdf"
        return build_patient_health_pdf(context), filename

    async def _load_medical_records(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> tuple[list[MedicalRecordDTO], int, bool]:
        normalized_from = _normalize_datetime(date_from)
        normalized_to = _normalize_datetime(date_to)

        collected: list[MedicalRecordDTO] = []
        page = 1
        page_size = 100

        while True:
            batch = await self._medical_records.list_medical_records(
                owner_id,
                patient_id=patient_id,
                page=page,
                page_size=page_size,
            )
            collected.extend(batch.items)
            if page >= batch.pages:
                break
            page += 1

        filtered = [
            record
            for record in collected
            if normalized_from <= _normalize_datetime(record.record_date) <= normalized_to
        ]
        filtered.sort(key=lambda item: item.record_date, reverse=True)
        total_in_range = len(filtered)
        truncated = total_in_range > MAX_MEDICAL_RECORDS_IN_REPORT
        return filtered[:MAX_MEDICAL_RECORDS_IN_REPORT], total_in_range, truncated

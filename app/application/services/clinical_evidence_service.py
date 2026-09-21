"""Load authorized clinical evidence for summary and future retrieval."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.application.clinical_summary.constants import EVIDENCE_FETCH_LIMIT
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle, ClinicalRetrievalDocumentDTO
from app.application.services.base import BaseService
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.patient import Patient
from app.domain.interfaces.appointment_repository import AppointmentRepository
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository
from app.domain.interfaces.medical_record_repository import MedicalRecordRepository
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository


def _in_window(
    at: datetime | None,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
) -> bool:
    if at is None:
        return date_from is None and date_to is None
    normalized = at if at.tzinfo else at.replace(tzinfo=UTC)
    if date_from is not None:
        start = date_from if date_from.tzinfo else date_from.replace(tzinfo=UTC)
        if normalized < start:
            return False
    if date_to is not None:
        end = date_to if date_to.tzinfo else date_to.replace(tzinfo=UTC)
        if normalized > end:
            return False
    return True


class ClinicalEvidenceService(BaseService):
    """Collect patient-scoped evidence after authorization has been resolved."""

    def __init__(
        self,
        health_measurement_repository: HealthMeasurementRepository,
        medical_record_repository: MedicalRecordRepository,
        appointment_repository: AppointmentRepository,
        risk_assessment_history_repository: RiskAssessmentHistoryRepository,
    ) -> None:
        self._measurements = health_measurement_repository
        self._medical_records = medical_record_repository
        self._appointments = appointment_repository
        self._risk_history = risk_assessment_history_repository

    async def load_evidence_bundle(
        self,
        patient: Patient,
        *,
        organization_id: UUID | None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ClinicalEvidenceBundle:
        patient_id = patient.id
        measurements = await self._measurements.list_by_patient_for_analytics(
            patient_id,
            date_from=date_from,
            date_to=date_to,
        )
        records = await self._medical_records.list_by_patient_ids(
            [patient_id],
            patient_id=patient_id,
            limit=EVIDENCE_FETCH_LIMIT,
        )
        appointments = await self._appointments.list_by_patient_ids(
            [patient_id],
            patient_id=patient_id,
            limit=EVIDENCE_FETCH_LIMIT,
        )
        history = await self._risk_history.list_by_patient(
            patient_id,
            evaluated_at_from=date_from,
            evaluated_at_to=date_to,
            offset=0,
            limit=EVIDENCE_FETCH_LIMIT,
        )

        records = [
            row
            for row in records
            if _in_window(row.record_date, date_from=date_from, date_to=date_to)
        ]
        appointments = [
            row
            for row in appointments
            if _in_window(row.appointment_date, date_from=date_from, date_to=date_to)
        ]

        bundle = ClinicalEvidenceBundle(
            patient=patient,
            organization_id=organization_id,
            medical_records=records,
            health_measurements=measurements,
            appointments=appointments,
            risk_assessment_history=history,
        )
        bundle.retrieval_documents = self._build_retrieval_documents(bundle)
        return bundle

    def _build_retrieval_documents(
        self,
        bundle: ClinicalEvidenceBundle,
    ) -> list[ClinicalRetrievalDocumentDTO]:
        docs: list[ClinicalRetrievalDocumentDTO] = []
        pid = bundle.patient.id
        org = bundle.organization_id

        for record in bundle.medical_records:
            docs.append(
                ClinicalRetrievalDocumentDTO(
                    evidence_id=f"{ClinicalEvidenceSourceType.MEDICAL_RECORD.value}:{record.id}",
                    patient_id=pid,
                    source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
                    source_id=record.id,
                    event_time=record.record_date,
                    content_fields={
                        "record_type": record.record_type,
                        "title": record.title,
                    },
                    organization_id=org,
                ),
            )

        for measurement in bundle.health_measurements:
            docs.append(
                ClinicalRetrievalDocumentDTO(
                    evidence_id=f"{ClinicalEvidenceSourceType.HEALTH_MEASUREMENT.value}:{measurement.id}",
                    patient_id=pid,
                    source_type=ClinicalEvidenceSourceType.HEALTH_MEASUREMENT,
                    source_id=measurement.id,
                    event_time=measurement.measured_at,
                    content_fields={"measured_at": measurement.measured_at.isoformat()},
                    organization_id=org,
                ),
            )

        for appointment in bundle.appointments:
            docs.append(
                ClinicalRetrievalDocumentDTO(
                    evidence_id=f"{ClinicalEvidenceSourceType.APPOINTMENT.value}:{appointment.id}",
                    patient_id=pid,
                    source_type=ClinicalEvidenceSourceType.APPOINTMENT,
                    source_id=appointment.id,
                    event_time=appointment.appointment_date,
                    content_fields={
                        "status": appointment.status,
                        "appointment_type": appointment.appointment_type,
                    },
                    organization_id=org,
                ),
            )

        for row in bundle.risk_assessment_history:
            docs.append(
                ClinicalRetrievalDocumentDTO(
                    evidence_id=f"{ClinicalEvidenceSourceType.RISK_ASSESSMENT_HISTORY.value}:{row.id}",
                    patient_id=pid,
                    source_type=ClinicalEvidenceSourceType.RISK_ASSESSMENT_HISTORY,
                    source_id=row.id,
                    event_time=row.evaluated_at,
                    content_fields={
                        "assessment_type": row.assessment_type.value,
                        "assessment_status": row.assessment_status,
                        "model_version": row.model_version,
                    },
                    organization_id=org,
                ),
            )

        return docs

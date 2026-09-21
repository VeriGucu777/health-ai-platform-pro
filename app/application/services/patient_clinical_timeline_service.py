"""Patient clinical timeline orchestration service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.application.analytics.clinical_timeline_builder import (
    apply_event_limit,
    filter_events_by_window,
    merge_and_sort_timeline_events,
)
from app.application.analytics.clinical_timeline_rules import (
    derived_trend_events,
    events_from_appointment,
    events_from_health_measurement,
    events_from_medical_record,
    risk_snapshot_event,
)
from app.application.dtos.patient_clinical_timeline import (
    PatientClinicalTimelineDTO,
    TimelineEventDTO,
    TimelineSourceDTO,
)
from app.application.services.base import BaseService
from app.application.services.diabetes_risk_assessment_service import DiabetesRiskAssessmentService
from app.application.services.heart_disease_risk_assessment_service import (
    HeartDiseaseRiskAssessmentService,
)
from app.application.dtos.medical_record import MedicalRecordDTO
from app.application.services.medical_record_service import MedicalRecordService
from app.application.services.patient_read_access import resolve_patient_read_access
from app.application.services.stroke_risk_assessment_service import StrokeRiskAssessmentService
from app.core.exceptions import ValidationError
from app.domain.entities.user import UserRole
from app.domain.interfaces.patient_access_policy import PatientAccessPolicy
from app.core.reference_ranges import CLINICAL_TIMELINE_DISCLAIMER, MAX_ANALYTICS_DATE_RANGE_DAYS
from app.domain.entities.clinical_timeline import ClinicalTimelineEvent
from app.domain.entities.medical_record import MedicalRecord
from app.domain.interfaces.appointment_repository import AppointmentRepository
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository
from app.domain.interfaces.patient_repository import PatientRepository

DEFAULT_MAX_EVENTS = 100
MAX_EVENTS_CAP = 200


class PatientClinicalTimelineService(BaseService):
    """Build a read-only clinical timeline for one owned patient."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        health_measurement_repository: HealthMeasurementRepository,
        medical_record_service: MedicalRecordService,
        appointment_repository: AppointmentRepository,
        diabetes_risk_service: DiabetesRiskAssessmentService,
        heart_risk_service: HeartDiseaseRiskAssessmentService,
        stroke_risk_service: StrokeRiskAssessmentService,
        access_policy: PatientAccessPolicy | None = None,
    ) -> None:
        self._patients = patient_repository
        self._health_measurements = health_measurement_repository
        self._medical_records = medical_record_service
        self._appointments = appointment_repository
        self._diabetes_risk = diabetes_risk_service
        self._heart_risk = heart_risk_service
        self._stroke_risk = stroke_risk_service
        self._access_policy = access_policy

    async def get_clinical_timeline(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        max_events: int = DEFAULT_MAX_EVENTS,
        include_risk_snapshot: bool = False,
    ) -> tuple[PatientClinicalTimelineDTO, UUID | None]:
        resolved = await resolve_patient_read_access(
            patients=self._patients,
            access_policy=self._access_policy,
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
        )
        resolved_to = _normalize_datetime(date_to or datetime.now(UTC))
        resolved_from = _normalize_datetime(date_from) if date_from is not None else None
        self._validate_date_range(resolved_from, resolved_to)
        capped_max_events = min(max(1, max_events), MAX_EVENTS_CAP)

        measurements = await self._health_measurements.list_by_patient_for_analytics(
            patient_id,
            date_from=resolved_from,
            date_to=resolved_to,
        )
        medical_records = await self._load_all_medical_records(
            actor_id,
            actor_role,
            patient_id=patient_id,
        )
        appointments = await self._load_all_appointments(patient_id=patient_id)

        generated_at = datetime.now(UTC)
        event_groups: list[list[ClinicalTimelineEvent]] = []

        for record_dto in medical_records:
            event_groups.append(events_from_medical_record(_medical_record_from_dto(record_dto)))
        for measurement in measurements:
            event_groups.append(events_from_health_measurement(measurement))
        for appointment in appointments:
            event_groups.append(
                events_from_appointment(appointment, as_of=generated_at),
            )

        event_groups.append(
            derived_trend_events(
                measurements,
                patient_id=patient_id,
                as_of=resolved_to,
            )
        )

        if include_risk_snapshot:
            event_groups.append(
                await self._build_risk_snapshot_events(
                    actor_id,
                    actor_role,
                    patient_id=patient_id,
                    date_from=resolved_from,
                    date_to=resolved_to,
                    assessed_at=generated_at,
                )
            )

        merged = merge_and_sort_timeline_events(event_groups)
        merged = filter_events_by_window(
            merged,
            date_from=resolved_from,
            date_to=resolved_to,
        )
        limited, truncated = apply_event_limit(merged, capped_max_events)

        timeline = PatientClinicalTimelineDTO(
            patient_id=patient_id,
            date_from=resolved_from,
            date_to=resolved_to,
            generated_at=generated_at,
            events=[_to_event_dto(event) for event in limited],
            truncated=truncated,
            disclaimer=CLINICAL_TIMELINE_DISCLAIMER,
        )
        return timeline, resolved.organization_id

    async def _load_all_medical_records(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
    ) -> list:
        collected = []
        page = 1
        page_size = 100
        while True:
            batch = await self._medical_records.list_medical_records(
                actor_id,
                actor_role,
                patient_id=patient_id,
                page=page,
                page_size=page_size,
            )
            collected.extend(batch.items)
            if page >= batch.pages:
                break
            page += 1
        return collected

    async def _load_all_appointments(self, *, patient_id: UUID) -> list:
        collected = []
        offset = 0
        limit = 100
        while True:
            batch = await self._appointments.list_by_patient_ids(
                [patient_id],
                offset=offset,
                limit=limit,
                patient_id=patient_id,
            )
            if not batch:
                break
            collected.extend(batch)
            if len(batch) < limit:
                break
            offset += limit
        return collected

    async def _build_risk_snapshot_events(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
        date_from: datetime | None,
        date_to: datetime,
        assessed_at: datetime,
    ) -> list[ClinicalTimelineEvent]:
        diabetes, _ = await self._diabetes_risk.assess_diabetes_risk(
            actor_id,
            actor_role,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        )
        heart, _ = await self._heart_risk.assess_heart_disease_risk(
            actor_id,
            actor_role,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        )
        stroke, _ = await self._stroke_risk.assess_stroke_risk(
            actor_id,
            actor_role,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        )
        return [
            risk_snapshot_event(
                patient_id=patient_id,
                disease="Diabetes",
                risk_level=diabetes.risk_level,
                score=diabetes.score,
                model_version=diabetes.model_version,
                assessed_at=assessed_at,
            ),
            risk_snapshot_event(
                patient_id=patient_id,
                disease="Heart disease",
                risk_level=heart.risk_level,
                score=heart.score,
                model_version=heart.model_version,
                assessed_at=assessed_at,
            ),
            risk_snapshot_event(
                patient_id=patient_id,
                disease="Stroke",
                risk_level=stroke.risk_level,
                score=stroke.score,
                model_version=stroke.model_version,
                assessed_at=assessed_at,
            ),
        ]

    def _validate_date_range(
        self,
        date_from: datetime | None,
        date_to: datetime,
    ) -> None:
        if date_from is not None and date_from > date_to:
            raise ValidationError("date_from must be before or equal to date_to")
        if date_from is not None and (date_to - date_from).days > MAX_ANALYTICS_DATE_RANGE_DAYS:
            raise ValidationError("Date range cannot exceed 366 days")


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _medical_record_from_dto(dto: MedicalRecordDTO) -> MedicalRecord:
    return MedicalRecord(
        id=dto.id,
        owner_id=dto.owner_id,
        patient_id=dto.patient_id,
        record_date=dto.record_date,
        record_type=dto.record_type,
        title=dto.title,
        description=dto.description,
        diagnosis=dto.diagnosis,
        treatment=dto.treatment,
        medications=dto.medications,
        doctor_name=dto.doctor_name,
        hospital_name=dto.hospital_name,
        notes=dto.notes,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )


def _to_event_dto(event: ClinicalTimelineEvent) -> TimelineEventDTO:
    return TimelineEventDTO(
        occurred_at=event.occurred_at,
        event_type=event.event_type,
        headline=event.headline,
        detail=event.detail,
        severity=event.severity,
        source=TimelineSourceDTO(kind=event.source.kind, id=event.source.id),
    )

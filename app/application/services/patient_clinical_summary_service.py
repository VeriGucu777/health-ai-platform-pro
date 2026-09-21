"""Deterministic clinical summary orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.application.analytics.clinical_summary_builder import build_deterministic_clinical_summary
from app.application.dtos.patient_clinical_summary import PatientClinicalSummaryDTO
from app.application.services.base import BaseService
from app.application.services.clinical_evidence_service import ClinicalEvidenceService
from app.application.services.patient_read_access import resolve_patient_read_access
from app.core.exceptions import ValidationError
from app.domain.entities.user import UserRole
from app.domain.interfaces.patient_access_policy import PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository


class PatientClinicalSummaryService(BaseService):
    """Authorize, load evidence, and build a deterministic clinical summary."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        clinical_evidence_service: ClinicalEvidenceService,
        access_policy: PatientAccessPolicy | None = None,
    ) -> None:
        self._patients = patient_repository
        self._evidence = clinical_evidence_service
        self._access_policy = access_policy

    async def get_clinical_summary(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[PatientClinicalSummaryDTO, UUID | None]:
        resolved = await resolve_patient_read_access(
            patients=self._patients,
            access_policy=self._access_policy,
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
        )
        resolved_from = _normalize_datetime(date_from) if date_from is not None else None
        resolved_to = _normalize_datetime(date_to) if date_to is not None else None
        self._validate_date_range(resolved_from, resolved_to)

        bundle = await self._evidence.load_evidence_bundle(
            resolved.patient,
            organization_id=resolved.organization_id,
            date_from=resolved_from,
            date_to=resolved_to,
        )
        generated_at = datetime.now(UTC)
        summary = build_deterministic_clinical_summary(
            bundle,
            date_from=resolved_from,
            date_to=resolved_to,
            generated_at=generated_at,
        )
        return summary, resolved.organization_id

    def _validate_date_range(
        self,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> None:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValidationError("date_from must be before or equal to date_to")


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

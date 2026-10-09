"""Clinical encounter audit event model (PHI-free, application layer)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.user import UserRole


@dataclass(frozen=True)
class ClinicalEncounterAuditEvent:
    """Single auditable encounter lifecycle signal."""

    operation: str
    actor_id: UUID
    actor_role: UserRole
    organization_id: UUID
    patient_id: UUID
    encounter_id: UUID | None = None
    child_kind: str | None = None
    child_id: UUID | None = None
    encounter_version: int | None = None
    encounter_status: str | None = None
    is_primary: bool | None = None
    negated: bool | None = None
    specialty_key: str | None = None
    result_count: int | None = None

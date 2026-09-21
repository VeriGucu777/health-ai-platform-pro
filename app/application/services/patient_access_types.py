"""Shared types for patient access resolution."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.patient import Patient


@dataclass(frozen=True)
class ResolvedPatientRead:
    """Patient entity plus policy context for downstream reads and audit."""

    patient: Patient
    organization_id: UUID | None

"""DTOs for patient consent management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.consent.enums import ConsentSource, ConsentStatus, ConsentType


class PatientConsentDTO(BaseModel):
    id: UUID
    patient_id: UUID
    organization_id: UUID
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: datetime
    revoked_at: datetime | None
    recorded_by_user_id: UUID
    version: int
    source: ConsentSource
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientConsentListDTO(BaseModel):
    organization_id: UUID
    items: list[PatientConsentDTO]

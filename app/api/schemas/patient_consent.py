"""API schemas for patient consent management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.consent.enums import ConsentSource, ConsentStatus, ConsentType


class PatientConsentGrant(BaseModel):
    consent_type: ConsentType = ConsentType.CLINICAL_DATA_PROCESSING


class PatientConsentResponse(BaseModel):
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


class PatientConsentListResponse(BaseModel):
    items: list[PatientConsentResponse] = Field(default_factory=list)

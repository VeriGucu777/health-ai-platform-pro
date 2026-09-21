"""Patient consent domain entities."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.consent.enums import ConsentSource, ConsentStatus, ConsentType


@dataclass(kw_only=True)
class PatientConsent:
    """Immutable history row for a patient consent decision within an organization."""

    id: UUID = field(default_factory=uuid4)
    patient_id: UUID
    organization_id: UUID
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: datetime
    revoked_at: datetime | None = None
    recorded_by_user_id: UUID
    version: int
    source: ConsentSource = ConsentSource.MANUAL
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

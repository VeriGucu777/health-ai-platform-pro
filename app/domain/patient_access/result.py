"""Patient access policy result model."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.patient_access.reason_codes import PatientAccessReasonCode


@dataclass(frozen=True)
class PatientAccessDecision:
    """Domain result of a patient access evaluation (HTTP mapping is external)."""

    allowed: bool
    reason_code: PatientAccessReasonCode
    organization_id: UUID | None = None
    suggested_http_status: int | None = None

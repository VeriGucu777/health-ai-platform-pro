"""Optional clinical consent enforcement (feature-flagged)."""

from __future__ import annotations

from uuid import UUID

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError
from app.domain.consent.enums import ConsentType
from app.domain.interfaces.patient_consent_repository import PatientConsentRepository


async def enforce_clinical_consent_if_required(
    *,
    settings: Settings | None,
    consent_repository: PatientConsentRepository | None,
    organization_id: UUID | None,
    patient_id: UUID,
) -> None:
    """When CLINICAL_CONSENT_ENFORCED=true, require active clinical_data_processing consent."""
    resolved_settings = settings or get_settings()
    if not resolved_settings.clinical_consent_enforced:
        return
    if organization_id is None:
        return
    if consent_repository is None:
        return

    active = await consent_repository.get_active_granted(
        patient_id,
        organization_id,
        ConsentType.CLINICAL_DATA_PROCESSING,
    )
    if active is None:
        raise ForbiddenError(
            "Clinical consent is required for this operation",
            details={"reason_code": "consent_required"},
        )

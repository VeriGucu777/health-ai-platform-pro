"""In-memory patient consent repository for API tests."""

from uuid import UUID

from app.domain.consent.entities import PatientConsent
from app.domain.consent.enums import ConsentStatus, ConsentType
from app.domain.interfaces.patient_consent_repository import PatientConsentRepository


class InMemoryPatientConsentRepository(PatientConsentRepository):
    """Append-only consent store keyed by consent id."""

    def __init__(self) -> None:
        self._consents: dict[UUID, PatientConsent] = {}

    async def get_by_id(self, entity_id: UUID) -> PatientConsent | None:
        return self._consents.get(entity_id)

    async def list_by_patient_and_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> list[PatientConsent]:
        rows = [
            consent
            for consent in self._consents.values()
            if consent.patient_id == patient_id and consent.organization_id == organization_id
        ]
        return sorted(rows, key=lambda row: row.created_at, reverse=True)

    async def get_active_granted(
        self,
        patient_id: UUID,
        organization_id: UUID,
        consent_type: ConsentType,
    ) -> PatientConsent | None:
        for consent in self._consents.values():
            if (
                consent.patient_id == patient_id
                and consent.organization_id == organization_id
                and consent.consent_type == consent_type
                and consent.status == ConsentStatus.GRANTED
            ):
                return consent
        return None

    async def get_max_version(
        self,
        patient_id: UUID,
        organization_id: UUID,
        consent_type: ConsentType,
    ) -> int:
        versions = [
            consent.version
            for consent in self._consents.values()
            if consent.patient_id == patient_id
            and consent.organization_id == organization_id
            and consent.consent_type == consent_type
        ]
        return max(versions, default=0)

    async def create(self, entity: PatientConsent) -> PatientConsent:
        self._consents[entity.id] = entity
        return entity

    async def update(self, entity: PatientConsent) -> PatientConsent:
        self._consents[entity.id] = entity
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        return self._consents.pop(entity_id, None) is not None

    def list_all(self) -> list[PatientConsent]:
        return list(self._consents.values())

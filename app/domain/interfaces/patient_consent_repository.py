"""Patient consent repository port."""

from abc import abstractmethod
from uuid import UUID

from app.domain.consent.entities import PatientConsent
from app.domain.consent.enums import ConsentType
from app.domain.interfaces.repository import Repository


class PatientConsentRepository(Repository[PatientConsent]):
    """Contract for patient consent persistence (append-only history)."""

    @abstractmethod
    async def list_by_patient_and_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> list[PatientConsent]:
        """Return consent history newest first."""

    @abstractmethod
    async def get_active_granted(
        self,
        patient_id: UUID,
        organization_id: UUID,
        consent_type: ConsentType,
    ) -> PatientConsent | None:
        """Return the active granted consent for the patient/org/type, if any."""

    @abstractmethod
    async def get_max_version(
        self,
        patient_id: UUID,
        organization_id: UUID,
        consent_type: ConsentType,
    ) -> int:
        """Return the highest version number recorded for the patient/org/type."""

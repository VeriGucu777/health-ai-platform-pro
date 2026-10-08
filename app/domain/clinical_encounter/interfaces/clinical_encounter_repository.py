"""Clinical encounter aggregate repository port."""

from abc import abstractmethod
from uuid import UUID

from app.domain.clinical_encounter.entities import ClinicalEncounter
from app.domain.interfaces.repository import Repository


class ClinicalEncounterRepository(Repository[ClinicalEncounter]):
    """Persistence contract for ClinicalEncounter aggregate (implementation in infrastructure)."""

    @abstractmethod
    async def list_for_patient(
        self,
        patient_id: UUID,
        *,
        organization_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ClinicalEncounter]:
        """List encounters for a patient, optionally scoped to an organization."""

    @abstractmethod
    async def get_active_for_patient(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> ClinicalEncounter | None:
        """Return the active encounter for patient/org if one exists (DB-enforced uniqueness later)."""

    @abstractmethod
    async def exists_active_for_patient(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """Check whether an active encounter exists without loading the full aggregate."""

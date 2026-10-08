"""Clinical encounter aggregate repository port."""

from abc import abstractmethod
from uuid import UUID

from app.domain.clinical_encounter.entities import ClinicalEncounterAggregate
from app.domain.interfaces.repository import Repository


class ClinicalEncounterRepository(Repository[ClinicalEncounterAggregate]):
    """Persistence contract for ClinicalEncounter aggregate (implementation in infrastructure)."""

    @abstractmethod
    async def add(self, aggregate: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
        """Persist a new encounter aggregate (flush only; caller owns commit)."""

    @abstractmethod
    async def save(self, aggregate: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
        """Persist aggregate changes with optimistic version checking."""

    @abstractmethod
    async def list_for_patient(
        self,
        patient_id: UUID,
        *,
        organization_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ClinicalEncounterAggregate]:
        """List encounters for a patient, optionally scoped to an organization."""

    @abstractmethod
    async def get_active_for_patient(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> ClinicalEncounterAggregate | None:
        """Return the active encounter for patient/org if one exists (DB-enforced uniqueness later)."""

    @abstractmethod
    async def exists_active_for_patient(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """Check whether an active encounter exists without loading the full aggregate."""

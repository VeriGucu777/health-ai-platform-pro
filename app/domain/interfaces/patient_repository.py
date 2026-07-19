"""Patient repository port."""

from abc import abstractmethod
from uuid import UUID

from app.domain.entities.patient import Patient
from app.domain.interfaces.repository import Repository


class PatientRepository(Repository[Patient]):
    """Contract for patient persistence scoped to an owning user."""

    @abstractmethod
    async def get_by_id_and_owner(self, patient_id: UUID, owner_id: UUID) -> Patient | None:
        """Retrieve a patient only when it belongs to the given owner."""

    @abstractmethod
    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        """List patients belonging to the given owner."""

    @abstractmethod
    async def count_by_owner(self, owner_id: UUID) -> int:
        """Count patients belonging to the given owner."""

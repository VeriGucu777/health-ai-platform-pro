"""Medical record repository port."""

from abc import abstractmethod
from uuid import UUID

from app.domain.entities.medical_record import MedicalRecord
from app.domain.interfaces.repository import Repository


class MedicalRecordRepository(Repository[MedicalRecord]):
    """Contract for medical record persistence scoped to an owning user."""

    @abstractmethod
    async def get_by_id_and_owner(
        self,
        medical_record_id: UUID,
        owner_id: UUID,
    ) -> MedicalRecord | None:
        """Retrieve a medical record only when it belongs to the given owner."""

    @abstractmethod
    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
        patient_id: UUID | None = None,
        record_type: str | None = None,
    ) -> list[MedicalRecord]:
        """List medical records belonging to the given owner."""

    @abstractmethod
    async def count_by_owner(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID | None = None,
        record_type: str | None = None,
    ) -> int:
        """Count medical records belonging to the given owner."""

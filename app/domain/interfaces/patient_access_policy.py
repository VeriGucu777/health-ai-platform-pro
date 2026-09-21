"""Patient access policy port."""

from abc import ABC, abstractmethod
from enum import StrEnum
from uuid import UUID

from app.domain.entities.user import UserRole
from app.domain.patient_access.result import PatientAccessDecision


class PatientAccessAction(StrEnum):
    """Clinical actions subject to patient access checks."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"


class PatientAccessPolicy(ABC):
    """Contract for organization- and assignment-aware patient access."""

    @abstractmethod
    async def resolve_access(
        self,
        *,
        actor_id: UUID,
        actor_role: UserRole,
        patient_id: UUID,
        action: PatientAccessAction,
    ) -> PatientAccessDecision:
        """Determine whether the actor may perform the action on the patient."""

    @abstractmethod
    async def resolve_create_access(
        self,
        *,
        actor_id: UUID,
        actor_role: UserRole,
    ) -> PatientAccessDecision:
        """Determine whether the actor may create a patient and which organization applies."""

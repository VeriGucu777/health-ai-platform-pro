"""Optional audit hook for clinical encounter lifecycle (Phase 1C.4 wiring)."""

from typing import Protocol
from uuid import UUID


class ClinicalEncounterAuditHook(Protocol):
    """Record encounter lifecycle events without coupling to AuditService yet."""

    async def encounter_created(
        self,
        *,
        encounter_id: UUID,
        patient_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
    ) -> None: ...

    async def encounter_viewed(
        self,
        *,
        encounter_id: UUID,
        patient_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
    ) -> None: ...


class NoOpClinicalEncounterAuditHook:
    """Default hook until API layer records audit events."""

    async def encounter_created(self, **kwargs: object) -> None:
        return None

    async def encounter_viewed(self, **kwargs: object) -> None:
        return None

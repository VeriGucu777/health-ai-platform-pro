"""Clinical encounter audit hook port (Phase 1C.4 concrete recorder in services)."""

from typing import Protocol

from app.application.clinical_encounter.audit_events import ClinicalEncounterAuditEvent


class ClinicalEncounterAuditHook(Protocol):
    """Record encounter lifecycle events; failures must propagate for mutations."""

    async def record_event(self, event: ClinicalEncounterAuditEvent) -> None: ...


class NoOpClinicalEncounterAuditHook:
    """Default until composition wires ClinicalEncounterAuditRecorder."""

    async def record_event(self, event: ClinicalEncounterAuditEvent) -> None:
        return None

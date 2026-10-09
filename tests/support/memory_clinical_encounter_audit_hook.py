"""In-memory clinical encounter audit hook for service unit tests."""

from __future__ import annotations

import copy

from app.application.clinical_encounter.audit_events import ClinicalEncounterAuditEvent


class MemoryClinicalEncounterAuditHook:
    """Records immutable copies of audit events (no PHI payloads)."""

    def __init__(self) -> None:
        self.events: list[ClinicalEncounterAuditEvent] = []

    async def record_event(self, event: ClinicalEncounterAuditEvent) -> None:
        self.events.append(copy.deepcopy(event))

    def clear(self) -> None:
        self.events.clear()


class FailingClinicalEncounterAuditHook:
    """Simulates audit persistence failure (fail-closed mutations)."""

    async def record_event(self, event: ClinicalEncounterAuditEvent) -> None:
        raise RuntimeError("audit persistence failed")

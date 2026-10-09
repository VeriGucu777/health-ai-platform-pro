"""Fail-closed clinical encounter audit recording via AuditService."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.application.clinical_encounter.audit_events import ClinicalEncounterAuditEvent
from app.application.dtos.audit_log import AuditRecordInput
from app.application.services.audit_service import AuditService
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType


def _action_for_event(event: ClinicalEncounterAuditEvent) -> AuditAction:
    if event.operation == "encounter_created":
        return AuditAction.CREATE
    if event.operation == "encounter_viewed":
        return AuditAction.VIEW
    if event.operation == "encounter_list_viewed":
        return AuditAction.LIST
    if event.operation == "child_deactivated":
        return AuditAction.DEACTIVATE
    return AuditAction.UPDATE


def _resource_id_for_event(event: ClinicalEncounterAuditEvent) -> UUID | None:
    if event.operation == "encounter_list_viewed":
        return event.patient_id
    return event.encounter_id


def _build_metadata(event: ClinicalEncounterAuditEvent) -> dict[str, Any]:
    meta: dict[str, Any] = {"operation": event.operation}
    if event.child_kind is not None:
        meta["child_kind"] = event.child_kind
    if event.child_id is not None:
        meta["child_id"] = str(event.child_id)
    if event.encounter_version is not None:
        meta["version"] = event.encounter_version
    if event.encounter_status is not None:
        meta["status"] = event.encounter_status
    if event.is_primary is not None:
        meta["is_primary"] = event.is_primary
    if event.negated is not None:
        meta["negated"] = event.negated
    if event.specialty_key is not None:
        meta["specialty_key"] = event.specialty_key
    if event.result_count is not None:
        meta["result_count"] = event.result_count
    return meta


class ClinicalEncounterAuditRecorder:
    """Maps encounter audit events to append-only AuditLog rows (raises on failure)."""

    def __init__(self, audit_service: AuditService) -> None:
        self._audit = audit_service

    async def record(self, event: ClinicalEncounterAuditEvent) -> None:
        entry = AuditRecordInput(
            resource_type=AuditResourceType.CLINICAL_ENCOUNTER,
            action=_action_for_event(event),
            outcome=AuditOutcome.SUCCESS,
            http_status=None,
            actor_id=event.actor_id,
            actor_role=event.actor_role,
            owner_scope_id=event.actor_id,
            resource_id=_resource_id_for_event(event),
            organization_id=event.organization_id,
            metadata=_build_metadata(event),
        )
        await self._audit.record(entry)

    async def record_event(self, event: ClinicalEncounterAuditEvent) -> None:
        await self.record(event)

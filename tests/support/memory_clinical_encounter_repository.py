"""In-memory clinical encounter aggregate repository for unit tests."""

from __future__ import annotations

import copy
from dataclasses import replace
from uuid import UUID

from app.domain.clinical_encounter.entities import (
    ClinicalEncounter,
    ClinicalEncounterAggregate,
    EncounterComplaint,
    EncounterFinalSummary,
    EncounterFinding,
    EncounterQuestionResponse,
)
from app.domain.clinical_encounter.enums import EncounterStatus
from app.domain.clinical_encounter.interfaces.clinical_encounter_repository import (
    ClinicalEncounterRepository,
)
from app.infrastructure.clinical_encounter.exceptions import (
    ClinicalEncounterConcurrencyError,
    ClinicalEncounterConflictError,
    ClinicalEncounterFinalSummaryConflictError,
)


def _clone_aggregate(aggregate: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
    return copy.deepcopy(aggregate)


def _operational_view(aggregate: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
    return ClinicalEncounterAggregate(
        encounter=copy.deepcopy(aggregate.encounter),
        complaints=tuple(
            c for c in aggregate.complaints if c.is_active and c.deleted_at is None
        ),
        findings=tuple(f for f in aggregate.findings if f.is_active and f.deleted_at is None),
        question_responses=tuple(
            r for r in aggregate.question_responses if r.is_active and r.deleted_at is None
        ),
        final_summary=copy.deepcopy(aggregate.final_summary) if aggregate.final_summary else None,
    )


class InMemoryClinicalEncounterRepository(ClinicalEncounterRepository):
    """Deterministic in-memory store with production-like invariants."""

    def __init__(self) -> None:
        self._aggregates: dict[UUID, ClinicalEncounterAggregate] = {}

    async def get_by_id(self, entity_id: UUID) -> ClinicalEncounterAggregate | None:
        stored = self._aggregates.get(entity_id)
        return _operational_view(stored) if stored else None

    async def create(self, entity: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
        return await self.add(entity)

    async def update(self, entity: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
        return await self.save(entity)

    async def delete(self, entity_id: UUID) -> bool:
        return self._aggregates.pop(entity_id, None) is not None

    async def add(self, aggregate: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
        if aggregate.encounter.id in self._aggregates:
            raise ClinicalEncounterConflictError("encounter id already exists")
        self._enforce_active_invariant(aggregate.encounter, exclude_id=None)
        self._enforce_appointment_unique(aggregate.encounter.appointment_id, exclude_id=None)
        self._enforce_child_invariants(aggregate)
        self._aggregates[aggregate.encounter.id] = _clone_aggregate(aggregate)
        return await self.get_by_id(aggregate.encounter.id)  # type: ignore[return-value]

    async def save(self, aggregate: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
        stored = self._aggregates.get(aggregate.encounter.id)
        if stored is None:
            raise ClinicalEncounterConcurrencyError("encounter not found for save")
        if stored.encounter.version != aggregate.encounter.version:
            raise ClinicalEncounterConcurrencyError("stale encounter version")
        if stored.final_summary is not None and aggregate.final_summary is not None:
            if stored.final_summary.id != aggregate.final_summary.id:
                raise ClinicalEncounterFinalSummaryConflictError(
                    "final summary already exists for encounter",
                )
        self._enforce_active_invariant(aggregate.encounter, exclude_id=aggregate.encounter.id)
        self._enforce_appointment_unique(
            aggregate.encounter.appointment_id,
            exclude_id=aggregate.encounter.id,
        )
        self._enforce_child_invariants(aggregate)
        updated_encounter = replace(aggregate.encounter, version=aggregate.encounter.version + 1)
        updated = ClinicalEncounterAggregate(
            encounter=updated_encounter,
            complaints=aggregate.complaints,
            findings=aggregate.findings,
            question_responses=aggregate.question_responses,
            final_summary=aggregate.final_summary,
        )
        self._aggregates[aggregate.encounter.id] = _clone_aggregate(updated)
        return await self.get_by_id(aggregate.encounter.id)  # type: ignore[return-value]

    async def list_for_patient(
        self,
        patient_id: UUID,
        *,
        organization_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ClinicalEncounterAggregate]:
        items = [
            agg
            for agg in self._aggregates.values()
            if agg.encounter.patient_id == patient_id
            and (organization_id is None or agg.encounter.organization_id == organization_id)
        ]
        items.sort(
            key=lambda agg: (
                agg.encounter.started_at or agg.encounter.created_at,
                agg.encounter.created_at,
            ),
            reverse=True,
        )
        page = items[offset : offset + limit]
        return [_operational_view(item) for item in page]

    async def get_active_for_patient(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> ClinicalEncounterAggregate | None:
        for agg in self._aggregates.values():
            enc = agg.encounter
            if (
                enc.patient_id == patient_id
                and enc.organization_id == organization_id
                and enc.status == EncounterStatus.ACTIVE
                and enc.is_active
                and enc.deleted_at is None
            ):
                return _operational_view(agg)
        return None

    async def exists_active_for_patient(self, patient_id: UUID, organization_id: UUID) -> bool:
        active = await self.get_active_for_patient(patient_id, organization_id)
        return active is not None

    def _enforce_active_invariant(self, encounter: ClinicalEncounter, *, exclude_id: UUID | None) -> None:
        if encounter.status != EncounterStatus.ACTIVE:
            return
        for agg in self._aggregates.values():
            if exclude_id is not None and agg.encounter.id == exclude_id:
                continue
            other = agg.encounter
            if (
                other.status == EncounterStatus.ACTIVE
                and other.patient_id == encounter.patient_id
                and other.organization_id == encounter.organization_id
                and other.is_active
                and other.deleted_at is None
            ):
                raise ClinicalEncounterConflictError("active encounter already exists for patient/org")

    def _enforce_appointment_unique(self, appointment_id: UUID | None, *, exclude_id: UUID | None) -> None:
        if appointment_id is None:
            return
        for agg in self._aggregates.values():
            if exclude_id is not None and agg.encounter.id == exclude_id:
                continue
            if agg.encounter.appointment_id == appointment_id:
                raise ClinicalEncounterConflictError("appointment already linked to encounter")

    def _enforce_child_invariants(self, aggregate: ClinicalEncounterAggregate) -> None:
        primary = [c for c in aggregate.complaints if c.is_primary and c.is_active and c.deleted_at is None]
        if len(primary) > 1:
            raise ClinicalEncounterConflictError("multiple primary complaints")
        keys = [
            r.question_key
            for r in aggregate.question_responses
            if r.is_active and r.deleted_at is None
        ]
        if len(keys) != len(set(keys)):
            raise ClinicalEncounterConflictError("duplicate active question_key")

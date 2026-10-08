"""In-memory clinical encounter repository tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.clinical_encounter.entities import (
    ClinicalEncounter,
    ClinicalEncounterAggregate,
    EncounterComplaint,
    EncounterFinalSummary,
    EncounterSummarySection,
)
from app.domain.clinical_encounter.enums import EncounterStatus
from app.infrastructure.clinical_encounter.exceptions import (
    ClinicalEncounterConcurrencyError,
    ClinicalEncounterConflictError,
    ClinicalEncounterFinalSummaryConflictError,
)
from tests.support.memory_clinical_encounter_repository import InMemoryClinicalEncounterRepository


def _aggregate(*, status: EncounterStatus = EncounterStatus.DRAFT) -> ClinicalEncounterAggregate:
    enc = ClinicalEncounter.create_draft(
        patient_id=uuid4(),
        organization_id=uuid4(),
        clinician_user_id=uuid4(),
        specialty_key="cardiology",
    )
    enc.status = status
    return ClinicalEncounterAggregate(encounter=enc)


@pytest.mark.asyncio
async def test_add_get_round_trip_and_copy_isolation() -> None:
    repo = InMemoryClinicalEncounterRepository()
    agg = _aggregate()
    stored = await repo.add(agg)
    loaded = await repo.get_by_id(stored.encounter.id)
    assert loaded is not None
    loaded.encounter.specialty_key = "mutated"
    again = await repo.get_by_id(stored.encounter.id)
    assert again is not None
    assert again.encounter.specialty_key == "cardiology"


@pytest.mark.asyncio
async def test_save_increments_version() -> None:
    repo = InMemoryClinicalEncounterRepository()
    agg = await repo.add(_aggregate())
    agg.encounter.status = EncounterStatus.ACTIVE
    saved = await repo.save(agg)
    assert saved.encounter.version == 2


@pytest.mark.asyncio
async def test_stale_version_rejected() -> None:
    repo = InMemoryClinicalEncounterRepository()
    agg = await repo.add(_aggregate())
    stale = await repo.get_by_id(agg.encounter.id)
    assert stale is not None
    await repo.save(stale)
    with pytest.raises(ClinicalEncounterConcurrencyError):
        await repo.save(agg)


@pytest.mark.asyncio
async def test_one_active_invariant() -> None:
    repo = InMemoryClinicalEncounterRepository()
    patient = uuid4()
    org = uuid4()
    first = ClinicalEncounter.create_draft(
        patient_id=patient,
        organization_id=org,
        clinician_user_id=uuid4(),
        specialty_key="cardiology",
    )
    first.status = EncounterStatus.ACTIVE
    await repo.add(ClinicalEncounterAggregate(encounter=first))
    second = ClinicalEncounter.create_draft(
        patient_id=patient,
        organization_id=org,
        clinician_user_id=uuid4(),
        specialty_key="cardiology",
    )
    second.status = EncounterStatus.ACTIVE
    with pytest.raises(ClinicalEncounterConflictError):
        await repo.add(ClinicalEncounterAggregate(encounter=second))


@pytest.mark.asyncio
async def test_final_summary_overwrite_rejected() -> None:
    repo = InMemoryClinicalEncounterRepository()
    enc = _aggregate()
    enc_id = enc.encounter.id
    summary_a = EncounterFinalSummary.create(
        encounter_id=enc_id,
        summary_version=1,
        summary_sections=(EncounterSummarySection(section_key="s"),),
        clinician_note=None,
        finalized_by=uuid4(),
        finalized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    stored = await repo.add(enc)
    with_summary = await repo.save(replace(stored, final_summary=summary_a))
    summary_b = EncounterFinalSummary.create(
        encounter_id=enc_id,
        summary_version=2,
        summary_sections=(EncounterSummarySection(section_key="s2"),),
        clinician_note=None,
        finalized_by=uuid4(),
        finalized_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    with pytest.raises(ClinicalEncounterFinalSummaryConflictError):
        await repo.save(replace(with_summary, final_summary=summary_b))

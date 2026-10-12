"""Phase 2E: wire semantic snapshot identity to encounter context assembly."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.application.clinical_decision.encounter_context_mapper import (
    EncounterContextAssemblyRequest,
    assemble_encounter_evaluation_context,
    assemble_encounter_evaluation_context_with_snapshot,
)
from app.application.clinical_decision.evaluation_context_snapshot import (
    evaluation_context_semantic_hash,
    snapshot_canonical_json_for_audit,
)
from app.application.clinical_decision.exceptions import UnknownClinicalVocabularyKeyError
from app.application.clinical_decision.vocabulary_eligibility import VocabularyEligibilityMode
from app.application.clinical_vocabulary.manifest_hash import vocabulary_manifest_hash
from app.domain.clinical_decision.models import PatientDemographicsInput
from app.domain.clinical_encounter.entities import (
    ClinicalEncounter,
    ClinicalEncounterAggregate,
    EncounterComplaint,
    EncounterFinalSummary,
    EncounterSummarySection,
)
from app.domain.clinical_vocabulary.enums import VocabularyCategory
from app.domain.clinical_vocabulary.interfaces.registry import ClinicalVocabularyRegistry
from app.domain.clinical_vocabulary.models import ControlledVocabularyItem, ControlledVocabularyManifest
from tests.unit.clinical_decision.test_encounter_context_mapper import _cardiology_registry

_PATIENT = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_ORG = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
_CLINICIAN = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
_T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
_T1 = datetime(2026, 3, 1, 11, 0, tzinfo=UTC)
_PHI = "SENTINEL_PHI_SNAPSHOT_WIRING_999"


def _encounter(*, version: int = 2) -> ClinicalEncounter:
    enc = ClinicalEncounter.create_draft(
        patient_id=_PATIENT,
        organization_id=_ORG,
        clinician_user_id=_CLINICIAN,
        specialty_key="cardiology",
        locale="tr",
    )
    enc.activate(at=_T0)
    enc.version = version
    return enc


def _request(
    agg: ClinicalEncounterAggregate,
    *,
    registry: ClinicalVocabularyRegistry | None = None,
    manifest_hash: str | None = None,
) -> EncounterContextAssemblyRequest:
    return EncounterContextAssemblyRequest(
        aggregate=agg,
        patient_demographics=PatientDemographicsInput(),
        vocabulary_registry=registry,
        vocabulary_manifest_hash=manifest_hash,
        reference_at=_T1,
    )


def test_assembly_result_contains_context_and_snapshot_id() -> None:
    enc = _encounter()
    agg = ClinicalEncounterAggregate(
        encounter=enc,
        complaints=(
            EncounterComplaint(
                encounter_id=enc.id,
                complaint_key="card.complaint.chest_pain",
                sequence_no=1,
            ),
        ),
    )
    reg = _cardiology_registry()
    result = assemble_encounter_evaluation_context_with_snapshot(
        _request(agg, registry=reg, manifest_hash="abc123"),
    )
    assert result.context.input_snapshot_id == result.snapshot.input_snapshot_id
    assert result.context.input_snapshot_id.startswith("sha256:")
    assert result.snapshot.encounter_version == enc.version


def test_same_semantic_context_same_snapshot_id() -> None:
    enc = _encounter()
    agg = ClinicalEncounterAggregate(
        encounter=enc,
        complaints=(
            EncounterComplaint(
                encounter_id=enc.id,
                complaint_key="card.complaint.chest_pain",
                sequence_no=1,
            ),
        ),
    )
    reg = _cardiology_registry()
    r1 = assemble_encounter_evaluation_context_with_snapshot(_request(agg, registry=reg))
    r2 = assemble_encounter_evaluation_context_with_snapshot(_request(agg, registry=reg))
    assert r1.snapshot.input_snapshot_id == r2.snapshot.input_snapshot_id


def test_structured_change_changes_snapshot_id() -> None:
    enc = _encounter()
    empty = ClinicalEncounterAggregate(encounter=enc)
    with_complaint = ClinicalEncounterAggregate(
        encounter=enc,
        complaints=(
            EncounterComplaint(
                encounter_id=enc.id,
                complaint_key="card.complaint.chest_pain",
                sequence_no=1,
            ),
        ),
    )
    reg = _cardiology_registry()
    h0 = assemble_encounter_evaluation_context_with_snapshot(
        _request(empty, registry=reg),
    ).snapshot.input_snapshot_id
    h1 = assemble_encounter_evaluation_context_with_snapshot(
        _request(with_complaint, registry=reg),
    ).snapshot.input_snapshot_id
    assert h0 != h1


def test_encounter_version_only_same_semantic_snapshot_different_metadata_version() -> None:
    enc_v2 = _encounter(version=2)
    enc_v5 = _encounter(version=5)
    complaint = (
        EncounterComplaint(
            encounter_id=enc_v2.id,
            complaint_key="card.complaint.chest_pain",
            sequence_no=1,
        ),
    )
    agg_v2 = ClinicalEncounterAggregate(encounter=enc_v2, complaints=complaint)
    agg_v5 = ClinicalEncounterAggregate(encounter=enc_v5, complaints=complaint)
    reg = _cardiology_registry()
    r2 = assemble_encounter_evaluation_context_with_snapshot(_request(agg_v2, registry=reg))
    r5 = assemble_encounter_evaluation_context_with_snapshot(_request(agg_v5, registry=reg))
    assert r2.snapshot.input_snapshot_id == r5.snapshot.input_snapshot_id
    assert r2.snapshot.encounter_version == 2
    assert r5.snapshot.encounter_version == 5


def test_vocabulary_identity_when_hash_supplied() -> None:
    enc = _encounter()
    agg = ClinicalEncounterAggregate(
        encounter=enc,
        complaints=(
            EncounterComplaint(
                encounter_id=enc.id,
                complaint_key="card.complaint.chest_pain",
                sequence_no=1,
            ),
        ),
    )
    reg = _cardiology_registry()
    result = assemble_encounter_evaluation_context_with_snapshot(
        _request(agg, registry=reg, manifest_hash="deadbeef"),
    )
    assert result.snapshot.vocabulary is not None
    assert result.snapshot.vocabulary.manifest_hash == "deadbeef"
    assert result.snapshot.vocabulary.vocabulary_id == "test"


def test_vocabulary_absent_still_assembles() -> None:
    enc = _encounter()
    agg = ClinicalEncounterAggregate(
        encounter=enc,
        complaints=(
            EncounterComplaint(
                encounter_id=enc.id,
                complaint_key="card.complaint.chest_pain",
                sequence_no=1,
            ),
        ),
    )
    result = assemble_encounter_evaluation_context_with_snapshot(
        _request(agg, registry=_cardiology_registry(), manifest_hash=None),
    )
    assert result.snapshot.vocabulary is None
    assert result.context.input_snapshot_id.startswith("sha256:")


def test_unknown_key_raises_no_snapshot() -> None:
    enc = _encounter()
    agg = ClinicalEncounterAggregate(
        encounter=enc,
        complaints=(
            EncounterComplaint(
                encounter_id=enc.id,
                complaint_key="card.complaint.unknown",
                sequence_no=1,
            ),
        ),
    )
    with pytest.raises(UnknownClinicalVocabularyKeyError):
        assemble_encounter_evaluation_context_with_snapshot(
            _request(agg, registry=_cardiology_registry()),
        )


def test_legacy_assemble_keeps_encounter_version_snapshot_id_format() -> None:
    enc = _encounter(version=3)
    agg = ClinicalEncounterAggregate(encounter=enc)
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            reference_at=_T1,
            validate_vocabulary_keys=False,
        ),
    )
    assert ctx.input_snapshot_id == f"{enc.id}:v3"


def test_phi_only_changes_do_not_change_semantic_snapshot() -> None:
    enc = _encounter()
    structured = EncounterComplaint(
        encounter_id=enc.id,
        complaint_key="card.complaint.chest_pain",
        sequence_no=1,
    )
    text_only = EncounterComplaint(
        encounter_id=enc.id,
        clinician_display_text=_PHI,
        sequence_no=2,
    )
    agg_a = ClinicalEncounterAggregate(encounter=enc, complaints=(structured,))
    agg_b = ClinicalEncounterAggregate(encounter=enc, complaints=(structured, text_only))
    reg = _cardiology_registry()
    id_a = assemble_encounter_evaluation_context_with_snapshot(
        _request(agg_a, registry=reg),
    ).snapshot.input_snapshot_id
    id_b = assemble_encounter_evaluation_context_with_snapshot(
        _request(agg_b, registry=reg),
    ).snapshot.input_snapshot_id
    assert id_a == id_b
    assert _PHI not in snapshot_canonical_json_for_audit(
        assemble_encounter_evaluation_context_with_snapshot(_request(agg_a, registry=reg)).context,
    )


def test_final_summary_does_not_affect_snapshot() -> None:
    enc = _encounter()
    summary = EncounterFinalSummary.create(
        encounter_id=enc.id,
        summary_version=1,
        summary_sections=(
            EncounterSummarySection(section_key="assessment", clinician_text=_PHI),
        ),
        clinician_note=_PHI,
        finalized_by=_CLINICIAN,
        finalized_at=_T1,
    )
    complaint = (
        EncounterComplaint(
            encounter_id=enc.id,
            complaint_key="card.complaint.chest_pain",
            sequence_no=1,
        ),
    )
    reg = _cardiology_registry()
    without = assemble_encounter_evaluation_context_with_snapshot(
        _request(
            ClinicalEncounterAggregate(encounter=enc, complaints=complaint),
            registry=reg,
        ),
    )
    with_summary = assemble_encounter_evaluation_context_with_snapshot(
        _request(
            ClinicalEncounterAggregate(
                encounter=enc,
                complaints=complaint,
                final_summary=summary,
            ),
            registry=reg,
        ),
    )
    assert without.snapshot.input_snapshot_id == with_summary.snapshot.input_snapshot_id


def test_production_eligibility_still_rejects_demo_vocabulary() -> None:
    enc = _encounter()
    agg = ClinicalEncounterAggregate(
        encounter=enc,
        complaints=(
            EncounterComplaint(
                encounter_id=enc.id,
                complaint_key="card.complaint.chest_pain",
                sequence_no=1,
            ),
        ),
    )
    with pytest.raises(UnknownClinicalVocabularyKeyError):
        assemble_encounter_evaluation_context_with_snapshot(
            EncounterContextAssemblyRequest(
                aggregate=agg,
                patient_demographics=PatientDemographicsInput(),
                vocabulary_registry=_cardiology_registry(),
                vocabulary_mode=VocabularyEligibilityMode.PRODUCTION,
                reference_at=_T1,
            ),
        )


def test_integration_real_registry_vocabulary_identity() -> None:
    from app.infrastructure.clinical_vocabulary.filesystem_registry import (
        FilesystemClinicalVocabularyRegistry,
    )

    registry = FilesystemClinicalVocabularyRegistry.default_cardiology()
    manifest = registry.manifest()
    m_hash = vocabulary_manifest_hash(manifest)
    enc = _encounter()
    agg = ClinicalEncounterAggregate(
        encounter=enc,
        complaints=(
            EncounterComplaint(
                encounter_id=enc.id,
                complaint_key="card.complaint.chest_pain",
                sequence_no=1,
            ),
        ),
    )
    result = assemble_encounter_evaluation_context_with_snapshot(
        _request(agg, registry=registry, manifest_hash=m_hash),
    )
    assert result.snapshot.vocabulary is not None
    assert result.snapshot.vocabulary.vocabulary_version == "1.0.0"
    assert evaluation_context_semantic_hash(result.context) in result.snapshot.input_snapshot_id

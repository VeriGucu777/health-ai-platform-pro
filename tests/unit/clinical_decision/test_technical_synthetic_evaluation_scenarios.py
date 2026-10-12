"""Phase 2H: neutral synthetic encounter fixtures and input provenance replay tests."""

from __future__ import annotations

import pytest

from app.application.clinical_decision.encounter_context_mapper import EncounterContextAssemblyRequest
from app.application.clinical_decision.evaluation_context_snapshot import (
    EvaluationContextSnapshotMetadata,
    snapshot_canonical_json_for_audit,
)
from app.application.clinical_decision.exceptions import UnknownClinicalVocabularyKeyError
from app.application.clinical_decision.vocabulary_eligibility import VocabularyEligibilityMode
from app.application.clinical_vocabulary.manifest_hash import vocabulary_manifest_hash
from app.domain.clinical_decision.models import PatientDemographicsInput
from tests.support.clinical_decision_scenarios import (
    PHI_SENTINEL,
    assemble_technical_scenario,
    scenario_001_minimal_structured,
    scenario_002_same_semantics_different_encounter_metadata,
    scenario_003_structured_input_change,
    scenario_004_phi_only_change,
    scenario_005_vital_ordering_pair,
    scenario_005_vital_ordering_scenario,
    scenario_complaint_insertion_order_reversed,
    scenario_duplicate_structured_complaint_keys,
    scenario_free_text_only_complaint,
    scenario_historical_context,
    scenario_unknown_vocabulary_key,
)
from tests.unit.clinical_decision.test_encounter_context_mapper import _cardiology_registry


def _demo_registry():
    return _cardiology_registry()


def test_scenario_001_assembles() -> None:
    result = assemble_technical_scenario(scenario_001_minimal_structured(), vocabulary_registry=_demo_registry())
    assert result.context.specialty_key == "cardiology"
    assert len(result.context.chief_complaints) == 1
    assert result.snapshot.input_snapshot_id.startswith("sha256:")


def test_scenario_001_snapshot_deterministic() -> None:
    scenario = scenario_001_minimal_structured()
    r1 = assemble_technical_scenario(scenario, vocabulary_registry=_demo_registry())
    r2 = assemble_technical_scenario(scenario, vocabulary_registry=_demo_registry())
    assert r1.snapshot.input_snapshot_id == r2.snapshot.input_snapshot_id


def test_scenario_002_non_semantic_metadata_same_semantic_id() -> None:
    a, b = scenario_002_same_semantics_different_encounter_metadata()
    reg = _demo_registry()
    id_a = assemble_technical_scenario(a, vocabulary_registry=reg).snapshot.input_snapshot_id
    id_b = assemble_technical_scenario(b, vocabulary_registry=reg).snapshot.input_snapshot_id
    assert id_a == id_b
    assert a.aggregate.encounter.id != b.aggregate.encounter.id


def test_scenario_003_structured_change_different_id() -> None:
    base, changed = scenario_003_structured_input_change()
    reg = _demo_registry()
    id_base = assemble_technical_scenario(base, vocabulary_registry=reg).snapshot.input_snapshot_id
    id_changed = assemble_technical_scenario(changed, vocabulary_registry=reg).snapshot.input_snapshot_id
    assert id_base != id_changed


def test_scenario_004_phi_only_same_semantic_id() -> None:
    base, with_phi = scenario_004_phi_only_change()
    reg = _demo_registry()
    id_base = assemble_technical_scenario(base, vocabulary_registry=reg).snapshot.input_snapshot_id
    id_phi = assemble_technical_scenario(with_phi, vocabulary_registry=reg).snapshot.input_snapshot_id
    assert id_base == id_phi
    audit = snapshot_canonical_json_for_audit(
        assemble_technical_scenario(with_phi, vocabulary_registry=reg).context,
    )
    assert PHI_SENTINEL not in audit


def test_alternate_insertion_order_deterministic_context_and_hash() -> None:
    a, b = scenario_complaint_insertion_order_reversed()
    reg = _demo_registry()
    ra = assemble_technical_scenario(a, vocabulary_registry=reg)
    rb = assemble_technical_scenario(b, vocabulary_registry=reg)
    assert ra.context.chief_complaints == rb.context.chief_complaints
    assert ra.snapshot.input_snapshot_id == rb.snapshot.input_snapshot_id


def test_vocabulary_identity_captured_real_registry() -> None:
    from app.infrastructure.clinical_vocabulary.filesystem_registry import (
        FilesystemClinicalVocabularyRegistry,
    )

    registry = FilesystemClinicalVocabularyRegistry.default_cardiology()
    manifest = registry.manifest()
    m_hash = vocabulary_manifest_hash(manifest)
    result = assemble_technical_scenario(
        scenario_001_minimal_structured(),
        vocabulary_registry=registry,
        vocabulary_manifest_hash=m_hash,
    )
    vocab = result.snapshot.vocabulary
    assert vocab is not None
    assert vocab.vocabulary_id == manifest.vocabulary_id
    assert vocab.vocabulary_version == "1.0.0"
    assert vocab.manifest_hash == m_hash


def test_production_mode_rejects_demo_vocabulary() -> None:
    scenario = scenario_001_minimal_structured()
    with pytest.raises(UnknownClinicalVocabularyKeyError):
        assemble_technical_scenario(
            scenario,
            vocabulary_registry=_demo_registry(),
            vocabulary_mode=VocabularyEligibilityMode.PRODUCTION,
        )


def test_unknown_key_fail_closed_no_snapshot() -> None:
    with pytest.raises(UnknownClinicalVocabularyKeyError):
        assemble_technical_scenario(
            scenario_unknown_vocabulary_key(),
            vocabulary_registry=_demo_registry(),
        )


def test_snapshot_envelope_fields_and_no_rule_manifest() -> None:
    scenario = scenario_001_minimal_structured()
    result = assemble_technical_scenario(scenario, vocabulary_registry=_demo_registry())
    snap = result.snapshot
    assert isinstance(snap, EvaluationContextSnapshotMetadata)
    assert snap.input_snapshot_id == result.context.input_snapshot_id
    assert snap.context_schema_version
    assert snap.encounter_id == result.context.encounter_id
    assert snap.specialty_key == "cardiology"
    assert snap.encounter_version == scenario.aggregate.encounter.version
    from dataclasses import fields

    field_names = {f.name for f in fields(snap)}
    assert "rule_manifest_hash" not in field_names
    ctx_json = result.context.model_dump_json()
    for forbidden in ("diagnosis", "probability", "recommendation"):
        assert forbidden not in ctx_json.lower()


def test_provenance_replay_same_semantic_id() -> None:
    scenario = scenario_001_minimal_structured()
    reg = _demo_registry()
    first = assemble_technical_scenario(scenario, vocabulary_registry=reg)
    replay = assemble_technical_scenario(scenario, vocabulary_registry=reg)
    assert first.snapshot.input_snapshot_id == replay.snapshot.input_snapshot_id


def test_mutation_isolation_after_assembly() -> None:
    scenario = scenario_001_minimal_structured()
    reg = _demo_registry()
    result = assemble_technical_scenario(scenario, vocabulary_registry=reg)
    frozen_context = result.context.model_dump()
    frozen_id = result.snapshot.input_snapshot_id
    complaint = scenario.aggregate.complaints[0]
    complaint.negated = True  # type: ignore[misc]
    assert result.context.model_dump() == frozen_context
    assert result.snapshot.input_snapshot_id == frozen_id


def test_duplicate_key_preservation_and_ordering() -> None:
    scenario = scenario_duplicate_structured_complaint_keys()
    ctx = assemble_technical_scenario(scenario, vocabulary_registry=_demo_registry()).context
    assert len(ctx.chief_complaints) == 2
    assert ctx.chief_complaints[0].negated is True
    assert ctx.chief_complaints[1].negated is False


def test_historical_context_changes_semantic_hash() -> None:
    reg = _demo_registry()
    off = assemble_technical_scenario(
        scenario_historical_context(has_risk_history=False),
        vocabulary_registry=reg,
    )
    on = assemble_technical_scenario(
        scenario_historical_context(has_risk_history=True),
        vocabulary_registry=reg,
    )
    assert off.snapshot.input_snapshot_id != on.snapshot.input_snapshot_id


def test_free_text_only_complaint_excluded_snapshot_still_built() -> None:
    result = assemble_technical_scenario(
        scenario_free_text_only_complaint(),
        vocabulary_registry=_demo_registry(),
    )
    assert result.context.chief_complaints == ()
    assert result.snapshot.input_snapshot_id.startswith("sha256:")


def test_scenario_005_vital_source_order_stable_hash() -> None:
    from app.infrastructure.clinical_vocabulary.filesystem_registry import (
        FilesystemClinicalVocabularyRegistry,
    )

    registry = FilesystemClinicalVocabularyRegistry.default_cardiology()
    order_ab, order_ba = scenario_005_vital_ordering_pair()
    sa = assemble_technical_scenario(
        scenario_005_vital_ordering_scenario(order_ab, scenario_suffix="ab"),
        vocabulary_registry=registry,
    )
    sb = assemble_technical_scenario(
        scenario_005_vital_ordering_scenario(order_ba, scenario_suffix="ba"),
        vocabulary_registry=registry,
    )
    assert sa.context.vitals == sb.context.vitals
    assert sa.snapshot.input_snapshot_id == sb.snapshot.input_snapshot_id


def test_no_rule_engine_imports_in_scenario_module() -> None:
    import tests.support.clinical_decision_scenarios as mod

    source = open(mod.__file__, encoding="utf-8").read()
    for forbidden in (
        "ClinicalDecisionOrchestrator",
        "RuleCatalogView",
        "ValidatedFilesystemClinicalRuleCatalogProvider",
    ):
        assert forbidden not in source

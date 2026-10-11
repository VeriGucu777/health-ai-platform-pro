"""Deterministic evaluation context snapshot and provenance foundation."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.clinical_decision.evaluation_context_snapshot import (
    CONTEXT_SCHEMA_VERSION,
    EvaluationContextSnapshotMetadata,
    build_evaluation_context_snapshot_metadata,
    canonical_semantic_json,
    evaluation_context_semantic_hash,
    input_snapshot_id_from_context,
    semantic_evaluation_context_payload,
    snapshot_canonical_json_for_audit,
    vocabulary_identity_from_manifest,
)
from app.application.clinical_vocabulary.manifest_hash import vocabulary_manifest_hash
from app.domain.clinical_decision.models import (
    EncounterComplaintInput,
    EncounterEvaluationContext,
    PatientDemographicsInput,
)
from app.domain.clinical_decision.enums import ClinicalInputSource
from tests.support.evaluation_context_fixtures import (
    context_with_complaint,
    context_with_historical_flags,
    context_with_vital,
    minimal_evaluation_context,
)

_PHI_MARKERS = (
    "clinician_display_text",
    "clinician_note",
    "clinician_text",
    "summary_sections",
    "first_name",
    "email",
    "phone",
    "address",
)


def test_same_context_produces_same_hash_and_snapshot_id() -> None:
    ctx = context_with_complaint()
    h1 = evaluation_context_semantic_hash(ctx)
    h2 = evaluation_context_semantic_hash(ctx)
    assert h1 == h2
    assert input_snapshot_id_from_context(ctx) == f"sha256:{h1}"


def test_canonical_json_stable_regardless_of_dict_construction_order() -> None:
    ctx = context_with_vital()
    payload_a = semantic_evaluation_context_payload(ctx)
    payload_b = copy.deepcopy(payload_a)
    reordered = {k: payload_b[k] for k in sorted(payload_b, reverse=True)}
    assert json.dumps(payload_a, sort_keys=True, separators=(",", ":")) == json.dumps(
        reordered,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert canonical_semantic_json(ctx) == json.dumps(
        payload_a,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def test_list_order_is_semantically_significant() -> None:
    t0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 3, 1, 10, 5, tzinfo=UTC)
    base = minimal_evaluation_context().model_dump()
    c1 = EncounterComplaintInput(
        complaint_key="card.complaint.chest_pain",
        recorded_at=t0,
    )
    c2 = EncounterComplaintInput(
        complaint_key="card.complaint.dyspnea",
        recorded_at=t1,
    )
    ctx_a = EncounterEvaluationContext.model_validate(
        {**base, "chief_complaints": (c1, c2)},
    )
    ctx_b = EncounterEvaluationContext.model_validate(
        {**base, "chief_complaints": (c2, c1)},
    )
    assert evaluation_context_semantic_hash(ctx_a) != evaluation_context_semantic_hash(ctx_b)


def test_identifier_and_envelope_fields_do_not_change_semantic_hash() -> None:
    ctx = context_with_complaint()
    h0 = evaluation_context_semantic_hash(ctx)
    altered = ctx.model_copy(
        update={
            "encounter_id": uuid4(),
            "patient_id": uuid4(),
            "clinician_user_id": uuid4(),
            "organization_id": uuid4(),
            "created_at": datetime(2099, 1, 1, tzinfo=UTC),
            "input_snapshot_id": "legacy:encounter:tag",
        },
    )
    assert evaluation_context_semantic_hash(altered) == h0


def test_structured_input_change_changes_hash() -> None:
    minimal = evaluation_context_semantic_hash(minimal_evaluation_context())
    with_complaint = evaluation_context_semantic_hash(context_with_complaint())
    assert minimal != with_complaint


def test_encounter_version_in_metadata_not_semantic_hash() -> None:
    ctx = context_with_complaint()
    meta_v1 = build_evaluation_context_snapshot_metadata(ctx, encounter_version=1)
    meta_v9 = build_evaluation_context_snapshot_metadata(ctx, encounter_version=9)
    assert meta_v1.input_snapshot_id == meta_v9.input_snapshot_id
    assert meta_v1.encounter_version == 1
    assert meta_v9.encounter_version == 9


def test_vital_measured_at_affects_hash() -> None:
    ctx = context_with_vital()
    h1 = evaluation_context_semantic_hash(ctx)
    vital = ctx.vitals[0]
    updated_vital = vital.model_copy(
        update={"recorded_at": datetime(2026, 3, 1, 12, 0, tzinfo=UTC)},
    )
    ctx2 = ctx.model_copy(update={"vitals": (updated_vital,)})
    assert evaluation_context_semantic_hash(ctx2) != h1


def test_float_canonicalization_is_deterministic() -> None:
    ctx_a = context_with_vital()
    ctx_b = ctx_a.model_copy(
        update={
            "vitals": (
                ctx_a.vitals[0].model_copy(update={"value_numeric": 72.0}),
            ),
        },
    )
    assert evaluation_context_semantic_hash(ctx_a) == evaluation_context_semantic_hash(ctx_b)
    canonical = snapshot_canonical_json_for_audit(ctx_a)
    assert "72" in canonical


def test_historical_context_flags_affect_hash() -> None:
    base = evaluation_context_semantic_hash(context_with_complaint())
    with_hist = evaluation_context_semantic_hash(context_with_historical_flags())
    assert base != with_hist


def test_phi_markers_absent_from_canonical_snapshot_source() -> None:
    ctx = context_with_complaint()
    audit_blob = snapshot_canonical_json_for_audit(ctx).lower()
    for marker in _PHI_MARKERS:
        assert marker not in audit_blob


def test_vocabulary_identity_in_metadata_only() -> None:
    from app.infrastructure.clinical_vocabulary.filesystem_registry import (
        FilesystemClinicalVocabularyRegistry,
    )

    registry = FilesystemClinicalVocabularyRegistry.default_cardiology()
    manifest = registry.manifest()
    v_hash = vocabulary_manifest_hash(manifest)
    identity = vocabulary_identity_from_manifest(manifest, v_hash)
    ctx = context_with_complaint()
    semantic = canonical_semantic_json(ctx)
    assert "manifest_hash" not in semantic
    meta = build_evaluation_context_snapshot_metadata(
        ctx,
        encounter_version=2,
        vocabulary=identity,
    )
    assert isinstance(meta, EvaluationContextSnapshotMetadata)
    assert meta.vocabulary is not None
    assert meta.vocabulary.manifest_hash == v_hash
    assert "rule" not in semantic.lower() or "historical_context" in semantic


def test_rule_manifest_not_in_semantic_hash_payload() -> None:
    payload = semantic_evaluation_context_payload(context_with_complaint())
    serialized = json.dumps(payload)
    assert "rule_manifest" not in serialized
    assert "rule_set" not in serialized


def test_empty_historical_null_normalized() -> None:
    ctx = minimal_evaluation_context()
    payload = semantic_evaluation_context_payload(ctx)
    assert payload["historical_context"] is None
    ctx_hist = context_with_historical_flags()
    payload_hist = semantic_evaluation_context_payload(ctx_hist)
    assert payload_hist["historical_context"] is not None

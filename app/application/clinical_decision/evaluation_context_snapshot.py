"""Deterministic semantic snapshot identity for EncounterEvaluationContext."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.clinical_decision.models import (
    ClinicalFindingInput,
    EncounterComplaintInput,
    EncounterEvaluationContext,
    EncounterHistoricalContext,
    PatientDemographicsInput,
    QuestionResponseInput,
    VitalObservationInput,
)
from app.domain.clinical_vocabulary.models import ControlledVocabularyManifest

CONTEXT_SCHEMA_VERSION = "encounter_evaluation_context_semantic:v1"
_HASH_PREFIX = "encounter_evaluation_context:v1:"


@dataclass(frozen=True, slots=True)
class VocabularySnapshotIdentity:
    vocabulary_id: str
    vocabulary_version: str
    manifest_hash: str


@dataclass(frozen=True, slots=True)
class EvaluationContextSnapshotMetadata:
    """Non-PHI envelope for replay and future evaluation provenance (input side)."""

    context_schema_version: str
    input_snapshot_id: str
    encounter_id: UUID
    encounter_version: int
    specialty_key: str
    encounter_context_assembly_version: str
    vocabulary: VocabularySnapshotIdentity | None = None
    historical_context_present: bool = False


@dataclass(frozen=True, slots=True)
class EvaluationProvenanceEnvelope:
    """Future full evaluation provenance (design); not wired to engine in Phase 2D."""

    input_snapshot_id: str
    context_schema_version: str
    vocabulary_manifest_hash: str | None
    rule_manifest_hash: str | None
    engine_version: str
    specialty_module_version: str
    policy_profile_id: str
    policy_profile_version: str
    evaluated_at: datetime


def vocabulary_identity_from_manifest(
    manifest: ControlledVocabularyManifest,
    manifest_hash: str,
) -> VocabularySnapshotIdentity:
    return VocabularySnapshotIdentity(
        vocabulary_id=manifest.vocabulary_id,
        vocabulary_version=manifest.vocabulary_version,
        manifest_hash=manifest_hash,
    )


def _iso_utc_seconds(value: datetime) -> str:
    if value.tzinfo is None:
        msg = "datetime must be timezone-aware for canonical snapshot"
        raise ValueError(msg)
    normalized = value.astimezone(UTC).replace(microsecond=0)
    text = normalized.isoformat()
    if text.endswith("+00:00"):
        return text[:-6] + "Z"
    return text


def _canonical_float(value: float) -> str:
    """Stable decimal text for hashing (not clinical rounding)."""
    decimal_value = Decimal(repr(value)).normalize()
    text = format(decimal_value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".") or "0"
    return text


def _demographics_payload(demo: PatientDemographicsInput) -> dict[str, Any]:
    return {
        "age_years": demo.age_years,
        "gender_key": demo.gender_key,
    }


def _complaint_payload(item: EncounterComplaintInput) -> dict[str, Any]:
    return {
        "complaint_key": item.complaint_key,
        "negated": item.negated,
        "source": item.source.value,
        "recorded_at": _iso_utc_seconds(item.recorded_at) if item.recorded_at else None,
    }


def _finding_payload(item: ClinicalFindingInput) -> dict[str, Any]:
    return {
        "finding_key": item.finding_key,
        "value_code": item.value_code,
        "negated": item.negated,
        "source": item.source.value,
        "recorded_at": _iso_utc_seconds(item.recorded_at) if item.recorded_at else None,
    }


def _vital_payload(item: VitalObservationInput) -> dict[str, Any]:
    numeric: str | None = None
    if item.value_numeric is not None:
        numeric = _canonical_float(item.value_numeric)
    return {
        "vital_key": item.vital_key,
        "value_numeric": numeric,
        "unit": item.unit,
        "source": item.source.value,
        "recorded_at": _iso_utc_seconds(item.recorded_at) if item.recorded_at else None,
    }


def _question_payload(item: QuestionResponseInput) -> dict[str, Any]:
    return {
        "question_key": item.question_key,
        "answer_code": item.answer_code,
        "recorded_at": _iso_utc_seconds(item.recorded_at) if item.recorded_at else None,
    }


def _historical_payload(hist: EncounterHistoricalContext | None) -> dict[str, Any] | None:
    if hist is None:
        return None
    return {
        "has_measurements": hist.has_measurements,
        "has_medical_records": hist.has_medical_records,
        "has_risk_history": hist.has_risk_history,
        "has_appointments": hist.has_appointments,
    }


def semantic_evaluation_context_payload(context: EncounterEvaluationContext) -> dict[str, Any]:
    """
    Structured clinical input only.

    Excludes encounter/patient/clinician identifiers, created_at, input_snapshot_id,
    and assembly envelope timestamps that are not part of structured clinical content.
    """
    return {
        "schema": CONTEXT_SCHEMA_VERSION,
        "specialty_key": context.specialty_key,
        "locale": context.locale,
        "patient_demographics": _demographics_payload(context.patient_demographics),
        "chief_complaints": [_complaint_payload(c) for c in context.chief_complaints],
        "findings": [_finding_payload(f) for f in context.findings],
        "vitals": [_vital_payload(v) for v in context.vitals],
        "question_responses": [_question_payload(q) for q in context.question_responses],
        "historical_context": _historical_payload(context.historical_context),
    }


def canonical_semantic_json(context: EncounterEvaluationContext) -> str:
    payload = semantic_evaluation_context_payload(context)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def evaluation_context_semantic_hash(context: EncounterEvaluationContext) -> str:
    body = canonical_semantic_json(context)
    digest = hashlib.sha256((_HASH_PREFIX + body).encode("utf-8")).hexdigest()
    return digest


def input_snapshot_id_from_context(context: EncounterEvaluationContext) -> str:
    return f"sha256:{evaluation_context_semantic_hash(context)}"


def build_evaluation_context_snapshot_metadata(
    context: EncounterEvaluationContext,
    *,
    encounter_version: int,
    vocabulary: VocabularySnapshotIdentity | None = None,
) -> EvaluationContextSnapshotMetadata:
    return EvaluationContextSnapshotMetadata(
        context_schema_version=CONTEXT_SCHEMA_VERSION,
        input_snapshot_id=input_snapshot_id_from_context(context),
        encounter_id=context.encounter_id,
        encounter_version=encounter_version,
        specialty_key=context.specialty_key,
        encounter_context_assembly_version=context.context_version,
        vocabulary=vocabulary,
        historical_context_present=context.historical_context is not None,
    )


def snapshot_canonical_json_for_audit(context: EncounterEvaluationContext) -> str:
    """Full canonical JSON used as hash input (for tests asserting PHI exclusion)."""
    return _HASH_PREFIX + canonical_semantic_json(context)

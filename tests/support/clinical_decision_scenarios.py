"""Neutral technical synthetic encounter scenarios for assembly/provenance tests (Phase 2H).

Not clinical golden cases — no medical correctness claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.application.clinical_decision.encounter_context_mapper import (
    EncounterContextAssemblyRequest,
    EncounterEvaluationContextAssemblyResult,
    assemble_encounter_evaluation_context_with_snapshot,
)
from app.application.clinical_decision.vocabulary_eligibility import VocabularyEligibilityMode
from app.domain.clinical_decision.models import (
    EncounterHistoricalContext,
    PatientDemographicsInput,
)
from app.domain.clinical_encounter.entities import (
    ClinicalEncounter,
    ClinicalEncounterAggregate,
    EncounterComplaint,
    EncounterFinalSummary,
    EncounterFinding,
    EncounterQuestionResponse,
    EncounterSummarySection,
)
from app.domain.clinical_encounter.enums import QuestionAnswerType
from app.domain.clinical_vocabulary.interfaces.registry import ClinicalVocabularyRegistry
from app.domain.entities.health_measurement import HealthMeasurement

# Stable technical IDs (synthetic, not real patients)
SCENARIO_PATIENT_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
SCENARIO_ORG_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
SCENARIO_CLINICIAN_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
SCENARIO_T0 = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)
SCENARIO_T1 = datetime(2026, 4, 1, 9, 30, tzinfo=UTC)
SCENARIO_T2 = datetime(2026, 4, 1, 9, 45, tzinfo=UTC)
PHI_SENTINEL = "SENTINEL_PHI_TECHNICAL_FIXTURE_2H"

MEASUREMENT_ID_A = UUID("11111111-1111-4111-8111-111111111111")
MEASUREMENT_ID_B = UUID("22222222-2222-4222-8222-222222222222")


@dataclass(frozen=True, slots=True)
class SyntheticEncounterScenario:
    """Technical fixture — no expected diagnosis, alerts, or clinical outputs."""

    scenario_id: str
    aggregate: ClinicalEncounterAggregate
    health_measurements: tuple[HealthMeasurement, ...] = ()
    historical_context: EncounterHistoricalContext | None = None
    notes: str = ""


def _activated_encounter(*, version: int = 2, activate_at: datetime | None = None) -> ClinicalEncounter:
    enc = ClinicalEncounter.create_draft(
        patient_id=SCENARIO_PATIENT_ID,
        organization_id=SCENARIO_ORG_ID,
        clinician_user_id=SCENARIO_CLINICIAN_ID,
        specialty_key="cardiology",
        locale="tr",
    )
    enc.activate(at=activate_at or SCENARIO_T0)
    enc.version = version
    return enc


def _structured_complaint(encounter_id: UUID, *, negated: bool = False, sequence_no: int = 1) -> EncounterComplaint:
    return EncounterComplaint(
        encounter_id=encounter_id,
        complaint_key="card.complaint.chest_pain",
        negated=negated,
        sequence_no=sequence_no,
    )


def scenario_001_minimal_structured() -> SyntheticEncounterScenario:
    """Minimal cardiology encounter with one structured complaint key."""
    enc = _activated_encounter()
    return SyntheticEncounterScenario(
        scenario_id="scenario_001",
        aggregate=ClinicalEncounterAggregate(
            encounter=enc,
            complaints=(_structured_complaint(enc.id),),
        ),
        notes="Baseline structured assembly",
    )


def scenario_002_same_semantics_different_encounter_metadata() -> tuple[SyntheticEncounterScenario, SyntheticEncounterScenario]:
    """Same structured input; different encounter id/version/activation time."""
    enc_a = _activated_encounter(version=2, activate_at=SCENARIO_T0)
    enc_b = _activated_encounter(version=7, activate_at=SCENARIO_T2)
    complaint_a = (_structured_complaint(enc_a.id),)
    complaint_b = (_structured_complaint(enc_b.id),)
    return (
        SyntheticEncounterScenario(
            scenario_id="scenario_002a",
            aggregate=ClinicalEncounterAggregate(encounter=enc_a, complaints=complaint_a),
            notes="Non-semantic metadata variant A",
        ),
        SyntheticEncounterScenario(
            scenario_id="scenario_002b",
            aggregate=ClinicalEncounterAggregate(encounter=enc_b, complaints=complaint_b),
            notes="Non-semantic metadata variant B",
        ),
    )


def scenario_003_structured_input_change() -> tuple[SyntheticEncounterScenario, SyntheticEncounterScenario]:
    """Base vs one structured field change (answer_code)."""
    base = scenario_001_minimal_structured()
    enc = base.aggregate.encounter
    with_response = SyntheticEncounterScenario(
        scenario_id="scenario_003",
        aggregate=ClinicalEncounterAggregate(
            encounter=enc,
            complaints=base.aggregate.complaints,
            question_responses=(
                EncounterQuestionResponse(
                    encounter_id=enc.id,
                    question_key="card.question.chest_pain_on_exertion",
                    answer_type=QuestionAnswerType.BOOLEAN,
                    answer_code="no",
                    sequence_no=1,
                ),
            ),
        ),
        notes="Structured answer_code differs from baseline",
    )
    return base, with_response


def scenario_004_phi_only_change() -> tuple[SyntheticEncounterScenario, SyntheticEncounterScenario]:
    """Structured input identical; PHI-only documentation added."""
    base = scenario_001_minimal_structured()
    enc = base.aggregate.encounter
    summary = EncounterFinalSummary.create(
        encounter_id=enc.id,
        summary_version=1,
        summary_sections=(
            EncounterSummarySection(section_key="assessment", clinician_text=PHI_SENTINEL),
        ),
        clinician_note=PHI_SENTINEL,
        finalized_by=SCENARIO_CLINICIAN_ID,
        finalized_at=SCENARIO_T1,
    )
    with_phi = SyntheticEncounterScenario(
        scenario_id="scenario_004",
        aggregate=ClinicalEncounterAggregate(
            encounter=enc,
            complaints=(
                EncounterComplaint(
                    encounter_id=enc.id,
                    complaint_key="card.complaint.chest_pain",
                    clinician_display_text=PHI_SENTINEL,
                    sequence_no=1,
                ),
                EncounterComplaint(
                    encounter_id=enc.id,
                    clinician_display_text=PHI_SENTINEL,
                    sequence_no=2,
                ),
            ),
            final_summary=summary,
        ),
        notes="PHI-only layers; structured complaint set unchanged",
    )
    return base, with_phi


def scenario_005_vital_ordering_pair() -> tuple[tuple[HealthMeasurement, ...], tuple[HealthMeasurement, ...]]:
    """Two measurements, same measured_at; reverse list order."""
    common = {
        "owner_id": SCENARIO_CLINICIAN_ID,
        "patient_id": SCENARIO_PATIENT_ID,
        "measured_at": SCENARIO_T1,
        "is_active": True,
    }
    m_a = HealthMeasurement(id=MEASUREMENT_ID_A, heart_rate=88, **common)
    m_b = HealthMeasurement(id=MEASUREMENT_ID_B, heart_rate=91, **common)
    order_ab = (m_a, m_b)
    order_ba = (m_b, m_a)
    return order_ab, order_ba


def scenario_005_vital_ordering_scenario(
    measurements: tuple[HealthMeasurement, ...],
    *,
    scenario_suffix: str,
) -> SyntheticEncounterScenario:
    base = scenario_001_minimal_structured()
    return SyntheticEncounterScenario(
        scenario_id=f"scenario_005_{scenario_suffix}",
        aggregate=base.aggregate,
        health_measurements=measurements,
        notes="Vital source order variant",
    )


def scenario_free_text_only_complaint() -> SyntheticEncounterScenario:
    enc = _activated_encounter()
    return SyntheticEncounterScenario(
        scenario_id="scenario_free_text_complaint",
        aggregate=ClinicalEncounterAggregate(
            encounter=enc,
            complaints=(
                EncounterComplaint(
                    encounter_id=enc.id,
                    clinician_display_text=PHI_SENTINEL,
                    sequence_no=1,
                ),
            ),
        ),
        notes="No complaint_key; free text only",
    )


def scenario_unknown_vocabulary_key() -> SyntheticEncounterScenario:
    enc = _activated_encounter()
    return SyntheticEncounterScenario(
        scenario_id="scenario_unknown_key",
        aggregate=ClinicalEncounterAggregate(
            encounter=enc,
            complaints=(
                EncounterComplaint(
                    encounter_id=enc.id,
                    complaint_key="card.complaint.not_in_vocabulary",
                    sequence_no=1,
                ),
            ),
        ),
        notes="Fail-closed vocabulary validation",
    )


def scenario_duplicate_structured_complaint_keys() -> SyntheticEncounterScenario:
    enc = _activated_encounter()
    return SyntheticEncounterScenario(
        scenario_id="scenario_duplicate_keys",
        aggregate=ClinicalEncounterAggregate(
            encounter=enc,
            complaints=(
                EncounterComplaint(
                    encounter_id=enc.id,
                    complaint_key="card.complaint.chest_pain",
                    negated=False,
                    sequence_no=2,
                ),
                EncounterComplaint(
                    encounter_id=enc.id,
                    complaint_key="card.complaint.chest_pain",
                    negated=True,
                    sequence_no=1,
                ),
            ),
        ),
        notes="Duplicate key, distinct structured negation state",
    )


def scenario_historical_context(*, has_risk_history: bool) -> SyntheticEncounterScenario:
    base = scenario_001_minimal_structured()
    return SyntheticEncounterScenario(
        scenario_id="scenario_historical",
        aggregate=base.aggregate,
        historical_context=EncounterHistoricalContext(
            has_measurements=False,
            has_medical_records=False,
            has_risk_history=has_risk_history,
            has_appointments=False,
        ),
        notes="Historical flags only",
    )


def scenario_complaint_insertion_order_reversed() -> tuple[SyntheticEncounterScenario, SyntheticEncounterScenario]:
    """Two structured complaints; tuple insertion order differs, sequence_no determines canonical order."""
    enc = _activated_encounter()
    c_low = EncounterComplaint(
        encounter_id=enc.id,
        complaint_key="card.complaint.chest_pain",
        negated=False,
        sequence_no=1,
    )
    c_high = EncounterComplaint(
        encounter_id=enc.id,
        complaint_key="card.complaint.chest_pain",
        negated=True,
        sequence_no=2,
    )
    agg_a = ClinicalEncounterAggregate(encounter=enc, complaints=(c_high, c_low))
    agg_b = ClinicalEncounterAggregate(encounter=enc, complaints=(c_low, c_high))
    return (
        SyntheticEncounterScenario(scenario_id="scenario_order_a", aggregate=agg_a),
        SyntheticEncounterScenario(scenario_id="scenario_order_b", aggregate=agg_b),
    )


def assemble_technical_scenario(
    scenario: SyntheticEncounterScenario,
    *,
    vocabulary_registry: ClinicalVocabularyRegistry | None,
    vocabulary_manifest_hash: str | None = None,
    vocabulary_mode: VocabularyEligibilityMode = VocabularyEligibilityMode.DEMO,
    reference_at: datetime | None = None,
) -> EncounterEvaluationContextAssemblyResult:
    """DEMO-mode assembly with snapshot metadata (no rule catalog)."""
    return assemble_encounter_evaluation_context_with_snapshot(
        EncounterContextAssemblyRequest(
            aggregate=scenario.aggregate,
            patient_demographics=PatientDemographicsInput(),
            historical_context=scenario.historical_context,
            health_measurements=scenario.health_measurements,
            vocabulary_registry=vocabulary_registry,
            vocabulary_manifest_hash=vocabulary_manifest_hash,
            vocabulary_mode=vocabulary_mode,
            reference_at=reference_at or SCENARIO_T1,
        ),
    )

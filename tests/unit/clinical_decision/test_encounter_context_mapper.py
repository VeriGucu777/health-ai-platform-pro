"""Encounter → EncounterEvaluationContext assembly (Phase 2C)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from app.application.clinical_decision.encounter_context_mapper import (
    EncounterContextAssemblyRequest,
    assemble_encounter_evaluation_context,
    context_contains_forbidden_phi_markers,
)
from app.application.clinical_decision.exceptions import UnknownClinicalVocabularyKeyError
from app.application.clinical_decision.historical_context import (
    encounter_historical_context_from_bundle,
)
from app.application.clinical_decision.vocabulary_eligibility import VocabularyEligibilityMode
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle
from app.domain.clinical_decision.models import PatientDemographicsInput
from app.domain.clinical_encounter.entities import (
    ClinicalEncounter,
    ClinicalEncounterAggregate,
    EncounterComplaint,
    EncounterFinalSummary,
    EncounterFinding,
    EncounterQuestionResponse,
    EncounterSummarySection,
)
from app.domain.clinical_encounter.enums import (
    ClinicalInputSource,
    FindingType,
    QuestionAnswerType,
)
from app.domain.clinical_vocabulary.enums import VocabularyCategory
from app.domain.clinical_vocabulary.interfaces.registry import ClinicalVocabularyRegistry
from app.domain.clinical_vocabulary.models import ControlledVocabularyItem, ControlledVocabularyManifest
from app.domain.entities.health_measurement import HealthMeasurement

_PATIENT = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_ORG = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
_CLINICIAN = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
_T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
_T1 = datetime(2026, 3, 1, 10, 30, tzinfo=UTC)
_PHI_SENTINEL = "SENTINEL_PHI_DO_NOT_LEAK_12345"


class _MemoryVocabularyRegistry(ClinicalVocabularyRegistry):
    def __init__(self, keys: dict[str, VocabularyCategory]) -> None:
        from app.domain.clinical_vocabulary.enums import (
            VocabularyClinicalReviewStatus,
            VocabularyItemStatus,
        )

        terms = tuple(
            ControlledVocabularyItem(
                key=k,
                category=cat,
                status=VocabularyItemStatus.APPROVED_DEMO,
                version_added="1.0.0",
                display_key=f"vocab.{k}",
                clinical_review_status=VocabularyClinicalReviewStatus.PROPOSED_BY_PRODUCT,
                engine_safe=False,
            )
            for k, cat in keys.items()
        )
        self._manifest = ControlledVocabularyManifest(
            vocabulary_id="test",
            vocabulary_version="1.0.0",
            specialty="cardiology",
            pilot_scope="test",
            manifest_clinical_review_status=VocabularyClinicalReviewStatus.PROPOSED_BY_PRODUCT,
            terms=terms,
        )
        self._by_key = {t.key: t for t in terms}

    def manifest(self) -> ControlledVocabularyManifest:
        return self._manifest

    def get(self, key: str) -> ControlledVocabularyItem | None:
        return self._by_key.get(key)

    def exists(self, key: str) -> bool:
        return key in self._by_key

    def list_by_category(self, category: VocabularyCategory) -> tuple[ControlledVocabularyItem, ...]:
        return tuple(t for t in self._manifest.terms if t.category == category)

    def list_by_specialty(self, specialty: str) -> tuple[ControlledVocabularyItem, ...]:
        return self._manifest.terms if specialty == "cardiology" else ()


def _cardiology_registry() -> _MemoryVocabularyRegistry:
    return _MemoryVocabularyRegistry(
        {
            "card.complaint.chest_pain": VocabularyCategory.COMPLAINT,
            "card.finding.smoking_history": VocabularyCategory.FINDING,
            "card.question.chest_pain_on_exertion": VocabularyCategory.QUESTION,
            "card.answer_code.yes": VocabularyCategory.ANSWER_CODE,
            "card.answer_code.no": VocabularyCategory.ANSWER_CODE,
            "card.answer_code.unknown": VocabularyCategory.ANSWER_CODE,
            "card.vital.heart_rate": VocabularyCategory.VITAL,
        },
    )


def _encounter() -> ClinicalEncounter:
    enc = ClinicalEncounter.create_draft(
        patient_id=_PATIENT,
        organization_id=_ORG,
        clinician_user_id=_CLINICIAN,
        specialty_key="cardiology",
        locale="tr",
    )
    enc.activate(at=_T0)
    return enc


def _minimal_aggregate(**kwargs: object) -> ClinicalEncounterAggregate:
    enc = _encounter()
    return ClinicalEncounterAggregate(
        encounter=enc,
        complaints=kwargs.get("complaints", ()),
        findings=kwargs.get("findings", ()),
        question_responses=kwargs.get("question_responses", ()),
        final_summary=kwargs.get("final_summary"),
    )


def test_minimal_encounter_maps_specialty_and_snapshot() -> None:
    agg = _minimal_aggregate()
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            reference_at=_T1,
            validate_vocabulary_keys=False,
        ),
    )
    assert ctx.specialty_key == "cardiology"
    assert ctx.locale == "tr"
    assert ctx.input_snapshot_id == f"{agg.encounter.id}:v{agg.encounter.version}"


def test_complaint_key_preserved_and_free_text_excluded() -> None:
    enc = _encounter()
    complaints = (
        EncounterComplaint(
            encounter_id=enc.id,
            complaint_key="card.complaint.chest_pain",
            clinician_display_text=_PHI_SENTINEL,
            sequence_no=1,
        ),
        EncounterComplaint(
            encounter_id=enc.id,
            clinician_display_text=_PHI_SENTINEL,
            sequence_no=2,
        ),
    )
    agg = ClinicalEncounterAggregate(encounter=enc, complaints=complaints)
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            vocabulary_registry=_cardiology_registry(),
            reference_at=_T1,
        ),
    )
    assert len(ctx.chief_complaints) == 1
    assert ctx.chief_complaints[0].complaint_key == "card.complaint.chest_pain"
    assert _PHI_SENTINEL not in ctx.model_dump_json()


def test_negation_and_ordering_complaints() -> None:
    enc = _encounter()
    c1 = EncounterComplaint(
        encounter_id=enc.id,
        complaint_key="card.complaint.chest_pain",
        sequence_no=2,
    )
    c2 = EncounterComplaint(
        encounter_id=enc.id,
        complaint_key="card.complaint.chest_pain",
        negated=True,
        sequence_no=1,
    )
    agg = ClinicalEncounterAggregate(encounter=enc, complaints=(c1, c2))
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            vocabulary_registry=_cardiology_registry(),
            reference_at=_T1,
        ),
    )
    assert len(ctx.chief_complaints) == 2
    assert ctx.chief_complaints[0].negated is True
    assert ctx.chief_complaints[1].negated is False


def test_inactive_complaint_excluded() -> None:
    enc = _encounter()
    active = EncounterComplaint(
        encounter_id=enc.id,
        complaint_key="card.complaint.chest_pain",
        sequence_no=1,
    )
    inactive = EncounterComplaint(
        encounter_id=enc.id,
        complaint_key="card.complaint.chest_pain",
        sequence_no=2,
        is_active=False,
    )
    agg = ClinicalEncounterAggregate(encounter=enc, complaints=(active, inactive))
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            vocabulary_registry=_cardiology_registry(),
            reference_at=_T1,
        ),
    )
    assert len(ctx.chief_complaints) == 1


def test_finding_mapped_decimal_preserved_on_aggregate() -> None:
    enc = _encounter()
    finding = EncounterFinding(
        encounter_id=enc.id,
        finding_type=FindingType.HISTORY_ITEM,
        finding_key="card.finding.smoking_history",
        value_numeric=Decimal("12.5"),
        unit="pack-years",
        sequence_no=1,
    )
    agg = ClinicalEncounterAggregate(encounter=enc, findings=(finding,))
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            vocabulary_registry=_cardiology_registry(),
            reference_at=_T1,
        ),
    )
    assert ctx.findings[0].finding_key == "card.finding.smoking_history"
    assert agg.findings[0].value_numeric == Decimal("12.5")


def test_question_answer_code_preserved_text_excluded() -> None:
    enc = _encounter()
    responses = (
        EncounterQuestionResponse(
            encounter_id=enc.id,
            question_key="card.question.chest_pain_on_exertion",
            answer_type=QuestionAnswerType.BOOLEAN,
            answer_code="yes",
            sequence_no=1,
        ),
        EncounterQuestionResponse(
            encounter_id=enc.id,
            question_key="card.question.chest_pain_on_exertion",
            answer_type=QuestionAnswerType.TEXT,
            clinician_note=_PHI_SENTINEL,
            sequence_no=2,
        ),
    )
    agg = ClinicalEncounterAggregate(encounter=enc, question_responses=responses)
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            vocabulary_registry=_cardiology_registry(),
            reference_at=_T1,
        ),
    )
    assert len(ctx.question_responses) == 1
    assert ctx.question_responses[0].answer_code == "yes"
    assert _PHI_SENTINEL not in ctx.model_dump_json()


def test_unknown_structured_key_fail_closed() -> None:
    enc = _encounter()
    complaint = EncounterComplaint(
        encounter_id=enc.id,
        complaint_key="card.complaint.unknown_term",
        sequence_no=1,
    )
    agg = ClinicalEncounterAggregate(encounter=enc, complaints=(complaint,))
    with pytest.raises(UnknownClinicalVocabularyKeyError):
        assemble_encounter_evaluation_context(
            EncounterContextAssemblyRequest(
                aggregate=agg,
                patient_demographics=PatientDemographicsInput(),
                vocabulary_registry=_cardiology_registry(),
                reference_at=_T1,
            ),
        )


def test_demo_vocabulary_allowed_production_mode_rejects() -> None:
    enc = _encounter()
    complaint = EncounterComplaint(
        encounter_id=enc.id,
        complaint_key="card.complaint.chest_pain",
        sequence_no=1,
    )
    agg = ClinicalEncounterAggregate(encounter=enc, complaints=(complaint,))
    with pytest.raises(UnknownClinicalVocabularyKeyError):
        assemble_encounter_evaluation_context(
            EncounterContextAssemblyRequest(
                aggregate=agg,
                patient_demographics=PatientDemographicsInput(),
                vocabulary_registry=_cardiology_registry(),
                vocabulary_mode=VocabularyEligibilityMode.PRODUCTION,
                reference_at=_T1,
            ),
        )


def test_vital_mapping_deterministic_from_measurements() -> None:
    enc = _encounter()
    m1 = HealthMeasurement(
        owner_id=_CLINICIAN,
        patient_id=_PATIENT,
        measured_at=_T0,
        heart_rate=80,
    )
    m2 = HealthMeasurement(
        owner_id=_CLINICIAN,
        patient_id=_PATIENT,
        measured_at=_T1,
        heart_rate=90,
    )
    agg = _minimal_aggregate()
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            health_measurements=(m2, m1),
            vocabulary_registry=_cardiology_registry(),
            reference_at=_T1,
        ),
    )
    assert len(ctx.vitals) == 2
    assert ctx.vitals[0].value_numeric == 80.0
    assert ctx.vitals[1].value_numeric == 90.0
    assert ctx.vitals[0].vital_key == "card.vital.heart_rate"


def test_historical_context_reused_from_bundle_helper() -> None:
    from app.domain.entities.patient import Patient

    patient = Patient(
        owner_id=_CLINICIAN,
        first_name="Test",
        last_name="Patient",
        date_of_birth=date(1980, 1, 1),
        gender="unknown",
    )
    bundle = ClinicalEvidenceBundle(
        patient=patient,
        health_measurements=[
            HealthMeasurement(
                owner_id=_CLINICIAN,
                patient_id=_PATIENT,
                measured_at=_T0,
                heart_rate=70,
            ),
        ],
    )
    hist = encounter_historical_context_from_bundle(bundle)
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=_minimal_aggregate(),
            patient_demographics=PatientDemographicsInput(),
            historical_context=hist,
            reference_at=_T1,
            validate_vocabulary_keys=False,
        ),
    )
    assert ctx.historical_context is not None
    assert ctx.historical_context.has_measurements is True


def test_final_summary_excluded() -> None:
    enc = _encounter()
    summary = EncounterFinalSummary.create(
        encounter_id=enc.id,
        summary_version=1,
        summary_sections=(
            EncounterSummarySection(section_key="assessment", clinician_text=_PHI_SENTINEL),
        ),
        clinician_note=_PHI_SENTINEL,
        finalized_by=_CLINICIAN,
        finalized_at=_T1,
    )
    agg = ClinicalEncounterAggregate(encounter=enc, final_summary=summary)
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            reference_at=_T1,
            validate_vocabulary_keys=False,
        ),
    )
    assert _PHI_SENTINEL not in ctx.model_dump_json()
    assert not context_contains_forbidden_phi_markers(ctx)


def test_same_input_equal_semantic_context() -> None:
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
    req = EncounterContextAssemblyRequest(
        aggregate=agg,
        patient_demographics=PatientDemographicsInput(age_years=40),
        vocabulary_registry=_cardiology_registry(),
        reference_at=_T1,
    )
    a = assemble_encounter_evaluation_context(req)
    b = assemble_encounter_evaluation_context(req)
    assert a.model_dump() == b.model_dump()


def test_context_mutation_does_not_alter_aggregate() -> None:
    enc = _encounter()
    complaint = EncounterComplaint(
        encounter_id=enc.id,
        complaint_key="card.complaint.chest_pain",
        sequence_no=1,
    )
    agg = ClinicalEncounterAggregate(encounter=enc, complaints=(complaint,))
    before = len(agg.complaints)
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            vocabulary_registry=_cardiology_registry(),
            reference_at=_T1,
        ),
    )
    with pytest.raises(Exception):
        ctx.locale = "en"  # type: ignore[misc]
    assert len(agg.complaints) == before


def test_no_clinical_outputs_in_context_model() -> None:
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=_minimal_aggregate(),
            patient_demographics=PatientDemographicsInput(),
            reference_at=_T1,
            validate_vocabulary_keys=False,
        ),
    )
    dumped = ctx.model_dump()
    assert "differential_candidates" not in dumped
    assert "safety_alerts" not in dumped


def test_integration_with_real_cardiology_vocabulary_registry() -> None:
    from app.infrastructure.clinical_vocabulary.filesystem_registry import (
        FilesystemClinicalVocabularyRegistry,
    )

    registry = FilesystemClinicalVocabularyRegistry.default_cardiology()
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
        question_responses=(
            EncounterQuestionResponse(
                encounter_id=enc.id,
                question_key="card.question.chest_pain_on_exertion",
                answer_type=QuestionAnswerType.BOOLEAN,
                answer_code="yes",
                sequence_no=1,
            ),
        ),
    )
    ctx = assemble_encounter_evaluation_context(
        EncounterContextAssemblyRequest(
            aggregate=agg,
            patient_demographics=PatientDemographicsInput(),
            vocabulary_registry=registry,
            reference_at=_T1,
        ),
    )
    assert ctx.chief_complaints[0].complaint_key == "card.complaint.chest_pain"
    assert registry.manifest().vocabulary_version == "1.0.0"

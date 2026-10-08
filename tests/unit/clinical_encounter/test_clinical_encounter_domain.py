"""Clinical encounter domain aggregate and child contract tests."""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from app.domain.clinical_encounter.entities import (
    ClinicalEncounter,
    EncounterComplaint,
    EncounterFinalSummary,
    EncounterFinding,
    EncounterQuestionResponse,
    EncounterSummarySection,
    assert_child_mutable_for_encounter,
)
from app.domain.clinical_encounter.enums import (
    ClinicalInputSource,
    EncounterStatus,
    FindingType,
    QuestionAnswerType,
)
from app.domain.clinical_encounter.exceptions import (
    EncounterAlreadyFinalizedError,
    EncounterCancelledError,
    EncounterImmutableError,
    InvalidEncounterComplaintError,
    InvalidEncounterFieldError,
    InvalidEncounterFindingError,
    InvalidEncounterFinalSummaryError,
    InvalidEncounterTransitionError,
    InvalidQuestionResponseError,
)

_PATIENT = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_ORG = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
_CLINICIAN = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
_ENCOUNTER = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
_T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
_T1 = datetime(2026, 3, 1, 11, 0, tzinfo=UTC)


def _draft() -> ClinicalEncounter:
    return ClinicalEncounter.create_draft(
        patient_id=_PATIENT,
        organization_id=_ORG,
        clinician_user_id=_CLINICIAN,
        specialty_key="cardiology",
        locale="tr",
    )


def test_create_valid_draft_encounter() -> None:
    enc = _draft()
    assert enc.status == EncounterStatus.DRAFT
    assert enc.version == 1
    assert enc.started_at is None
    assert enc.specialty_key == "cardiology"


def test_draft_to_active() -> None:
    enc = _draft()
    enc.activate(at=_T0)
    assert enc.status == EncounterStatus.ACTIVE
    assert enc.started_at == _T0
    assert enc.version == 2


def test_active_to_finalized() -> None:
    enc = _draft()
    enc.activate(at=_T0)
    enc.finalize(at=_T1)
    assert enc.status == EncounterStatus.FINALIZED
    assert enc.ended_at == _T1
    assert enc.is_terminal()


def test_active_to_cancelled() -> None:
    enc = _draft()
    enc.activate(at=_T0)
    enc.cancel(at=_T1)
    assert enc.status == EncounterStatus.CANCELLED
    assert enc.ended_at == _T1


def test_draft_to_cancelled() -> None:
    enc = _draft()
    enc.cancel(at=_T0)
    assert enc.status == EncounterStatus.CANCELLED
    assert enc.ended_at == _T0


def test_finalized_to_active_rejected() -> None:
    enc = _draft()
    enc.activate(at=_T0)
    enc.finalize(at=_T1)
    with pytest.raises(InvalidEncounterTransitionError):
        enc.activate(at=_T1)


def test_finalized_to_cancel_rejected() -> None:
    enc = _draft()
    enc.activate(at=_T0)
    enc.finalize(at=_T1)
    with pytest.raises(EncounterAlreadyFinalizedError):
        enc.cancel(at=_T1)


def test_cancelled_to_active_rejected() -> None:
    enc = _draft()
    enc.cancel(at=_T0)
    with pytest.raises(InvalidEncounterTransitionError):
        enc.activate(at=_T1)


def test_ended_at_before_started_at_rejected() -> None:
    with pytest.raises(InvalidEncounterFieldError):
        ClinicalEncounter(
            patient_id=_PATIENT,
            organization_id=_ORG,
            clinician_user_id=_CLINICIAN,
            specialty_key="cardiology",
            status=EncounterStatus.ACTIVE,
            started_at=_T1,
            ended_at=_T0,
        )


def test_version_less_than_one_rejected() -> None:
    with pytest.raises(InvalidEncounterFieldError):
        ClinicalEncounter(
            patient_id=_PATIENT,
            organization_id=_ORG,
            clinician_user_id=_CLINICIAN,
            specialty_key="cardiology",
            version=0,
        )


def test_specialty_key_empty_rejected() -> None:
    with pytest.raises(InvalidEncounterFieldError):
        ClinicalEncounter.create_draft(
            patient_id=_PATIENT,
            organization_id=_ORG,
            clinician_user_id=_CLINICIAN,
            specialty_key="  ",
        )


def test_complaint_requires_key_or_display_text() -> None:
    with pytest.raises(InvalidEncounterComplaintError):
        EncounterComplaint(encounter_id=_ENCOUNTER, sequence_no=1)


def test_complaint_sequence_non_positive_rejected() -> None:
    with pytest.raises(InvalidEncounterComplaintError):
        EncounterComplaint(
            encounter_id=_ENCOUNTER,
            complaint_key="copilot.test.complaint",
            sequence_no=0,
        )


def test_finding_requires_finding_key() -> None:
    with pytest.raises(InvalidEncounterFindingError):
        EncounterFinding(
            encounter_id=_ENCOUNTER,
            finding_type=FindingType.SYMPTOM,
            finding_key="  ",
        )


def test_number_question_requires_answer_numeric() -> None:
    with pytest.raises(InvalidQuestionResponseError):
        EncounterQuestionResponse(
            encounter_id=_ENCOUNTER,
            question_key="copilot.test.q",
            answer_type=QuestionAnswerType.NUMBER,
        )


def test_single_choice_requires_answer_code() -> None:
    with pytest.raises(InvalidQuestionResponseError):
        EncounterQuestionResponse(
            encounter_id=_ENCOUNTER,
            question_key="copilot.test.q",
            answer_type=QuestionAnswerType.SINGLE_CHOICE,
        )


def test_text_answer_marks_non_engine_evaluable() -> None:
    resp = EncounterQuestionResponse(
        encounter_id=_ENCOUNTER,
        question_key="copilot.test.q",
        answer_type=QuestionAnswerType.TEXT,
        clinician_note="free text only",
    )
    assert resp.is_engine_evaluable() is False


def test_finalized_encounter_assert_mutable_rejected() -> None:
    enc = _draft()
    enc.activate(at=_T0)
    enc.finalize(at=_T1)
    with pytest.raises(EncounterAlreadyFinalizedError):
        enc.assert_mutable()


def test_active_encounter_assert_mutable_allowed() -> None:
    enc = _draft()
    enc.activate(at=_T0)
    enc.assert_mutable()
    assert_child_mutable_for_encounter(enc)


def test_final_summary_immutable_and_structured() -> None:
    section = EncounterSummarySection(section_key="assessment", content_key="generic.placeholder")
    summary = EncounterFinalSummary.create(
        encounter_id=_ENCOUNTER,
        summary_version=1,
        summary_sections=(section,),
        clinician_note="note",
        finalized_by=_CLINICIAN,
        finalized_at=_T1,
    )
    with pytest.raises(AttributeError):
        summary.summary_version = 2  # type: ignore[misc]
    with pytest.raises(InvalidEncounterFinalSummaryError):
        EncounterFinalSummary.create(
            encounter_id=_ENCOUNTER,
            summary_version=1,
            summary_sections=(),
            clinician_note=None,
            finalized_by=_CLINICIAN,
            finalized_at=_T1,
        )


def test_complaint_display_text_not_in_repr() -> None:
    complaint = EncounterComplaint(
        encounter_id=_ENCOUNTER,
        clinician_display_text="PHI secret complaint",
        sequence_no=1,
    )
    assert "PHI secret" not in repr(complaint)


def test_finding_numeric_requires_unit() -> None:
    with pytest.raises(InvalidEncounterFindingError):
        EncounterFinding(
            encounter_id=_ENCOUNTER,
            finding_type=FindingType.OTHER,
            finding_key="copilot.test.finding",
            value_numeric=Decimal("1.0"),
        )


def test_cancelled_encounter_assert_mutable_raises() -> None:
    enc = _draft()
    enc.cancel(at=_T0)
    with pytest.raises(EncounterCancelledError):
        enc.assert_mutable()


def test_soft_deleted_encounter_assert_mutable_raises() -> None:
    enc = _draft()
    enc.activate(at=_T0)
    enc.is_active = False
    with pytest.raises(EncounterImmutableError):
        enc.assert_mutable()


def test_domain_import_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    root = repo_root / "app/domain/clinical_encounter"
    forbidden = frozenset({"fastapi", "sqlalchemy", "httpx", "requests", "openai"})
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden


def test_boolean_answer_normalizes_code() -> None:
    resp = EncounterQuestionResponse(
        encounter_id=_ENCOUNTER,
        question_key="copilot.test.q",
        answer_type=QuestionAnswerType.BOOLEAN,
        answer_code="YES",
    )
    assert resp.answer_code == "yes"
    assert resp.is_engine_evaluable() is True


def test_naive_datetime_rejected_on_activate() -> None:
    enc = _draft()
    with pytest.raises(InvalidEncounterFieldError):
        enc.activate(at=datetime(2026, 1, 1, 12, 0, 0))

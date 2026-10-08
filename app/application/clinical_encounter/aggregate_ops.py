"""Pure aggregate helpers for encounter application workflows."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.domain.clinical_encounter.entities import (
    ClinicalEncounterAggregate,
    EncounterComplaint,
    EncounterFinding,
    EncounterQuestionResponse,
    assert_child_mutable_for_encounter,
)
from app.domain.clinical_encounter.enums import QuestionAnswerType


def next_child_sequence_no(aggregate: ClinicalEncounterAggregate) -> int:
    """Next sequence number across all child rows (including inactive history)."""
    sequences: list[int] = []
    sequences.extend(c.sequence_no for c in aggregate.complaints)
    sequences.extend(f.sequence_no for f in aggregate.findings)
    sequences.extend(r.sequence_no for r in aggregate.question_responses)
    if not sequences:
        return 1
    return max(sequences) + 1


def soft_deactivate_encounter_child(
    child: EncounterComplaint | EncounterFinding | EncounterQuestionResponse,
    *,
    at: datetime,
) -> EncounterComplaint | EncounterFinding | EncounterQuestionResponse:
    """Soft-deactivate a child row (no hard delete)."""
    return replace(
        child,
        is_active=False,
        deleted_at=at,
    )


def append_complaint(
    aggregate: ClinicalEncounterAggregate,
    *,
    complaint_key: str | None,
    clinician_display_text: str | None,
    is_primary: bool,
    negated: bool,
    recorded_at: datetime,
    recorded_by: UUID,
) -> ClinicalEncounterAggregate:
    assert_child_mutable_for_encounter(aggregate.encounter)
    seq = next_child_sequence_no(aggregate)
    complaint = EncounterComplaint(
        encounter_id=aggregate.encounter.id,
        complaint_key=complaint_key,
        clinician_display_text=clinician_display_text,
        is_primary=is_primary,
        negated=negated,
        sequence_no=seq,
        recorded_at=recorded_at,
        recorded_by=recorded_by,
    )
    complaints = aggregate.complaints + (complaint,)
    if is_primary:
        adjusted: list[EncounterComplaint] = []
        for existing in complaints:
            if existing.id != complaint.id and existing.is_primary and existing.is_active:
                adjusted.append(
                    replace(
                        existing,
                        is_active=False,
                        deleted_at=recorded_at,
                    ),
                )
            else:
                adjusted.append(existing)
        complaints = tuple(adjusted)
    return replace(aggregate, complaints=complaints)


def append_finding(
    aggregate: ClinicalEncounterAggregate,
    *,
    finding: EncounterFinding,
) -> ClinicalEncounterAggregate:
    assert_child_mutable_for_encounter(aggregate.encounter)
    seq = next_child_sequence_no(aggregate)
    finding = replace(finding, encounter_id=aggregate.encounter.id, sequence_no=seq)
    return replace(aggregate, findings=aggregate.findings + (finding,))


def record_question_response(
    aggregate: ClinicalEncounterAggregate,
    *,
    question_key: str,
    answer_type: QuestionAnswerType,
    answer_code: str | None,
    answer_numeric,
    clinician_note: str | None,
    answered_at: datetime,
    answered_by: UUID,
) -> ClinicalEncounterAggregate:
    assert_child_mutable_for_encounter(aggregate.encounter)
    retained: list[EncounterQuestionResponse] = []
    for existing in aggregate.question_responses:
        if (
            existing.question_key == question_key
            and existing.is_active
            and existing.deleted_at is None
        ):
            retained.append(
                soft_deactivate_encounter_child(existing, at=answered_at),  # type: ignore[arg-type]
            )
        else:
            retained.append(existing)
    seq = next_child_sequence_no(replace(aggregate, question_responses=tuple(retained)))
    response = EncounterQuestionResponse(
        encounter_id=aggregate.encounter.id,
        question_key=question_key,
        answer_type=answer_type,
        answer_code=answer_code,
        answer_numeric=answer_numeric,
        clinician_note=clinician_note,
        sequence_no=seq,
        answered_at=answered_at,
        answered_by=answered_by,
    )
    return replace(aggregate, question_responses=tuple(retained) + (response,))


def deactivate_complaint_by_id(
    aggregate: ClinicalEncounterAggregate,
    complaint_id: UUID,
    *,
    at: datetime,
) -> ClinicalEncounterAggregate:
    assert_child_mutable_for_encounter(aggregate.encounter)
    updated: list[EncounterComplaint] = []
    found = False
    for complaint in aggregate.complaints:
        if complaint.id == complaint_id:
            found = True
            updated.append(soft_deactivate_encounter_child(complaint, at=at))  # type: ignore[arg-type]
        else:
            updated.append(complaint)
    if not found:
        return aggregate
    return replace(aggregate, complaints=tuple(updated))


def utc_now_fallback() -> datetime:
    return datetime.now(UTC)

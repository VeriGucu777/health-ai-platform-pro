"""Map clinical encounter aggregates to API response models."""

from __future__ import annotations

from app.api.schemas.clinical_encounter import (
    ClinicalEncounterDetailResponse,
    ClinicalEncounterListResponse,
    ClinicalEncounterSummaryResponse,
    EncounterComplaintResponse,
    EncounterFinalSummaryResponse,
    EncounterFindingResponse,
    EncounterQuestionResponseItem,
    EncounterSummarySectionResponse,
)
from app.domain.clinical_encounter.entities import (
    ClinicalEncounterAggregate,
    EncounterComplaint,
    EncounterFinalSummary,
    EncounterFinding,
    EncounterQuestionResponse,
    EncounterSummarySection,
)


def _active_complaints(aggregate: ClinicalEncounterAggregate) -> tuple[EncounterComplaint, ...]:
    return tuple(
        c for c in aggregate.complaints if c.is_active and c.deleted_at is None
    )


def _active_findings(aggregate: ClinicalEncounterAggregate) -> tuple[EncounterFinding, ...]:
    return tuple(f for f in aggregate.findings if f.is_active and f.deleted_at is None)


def _active_responses(
    aggregate: ClinicalEncounterAggregate,
) -> tuple[EncounterQuestionResponse, ...]:
    return tuple(
        r for r in aggregate.question_responses if r.is_active and r.deleted_at is None
    )


def encounter_summary_response(aggregate: ClinicalEncounterAggregate) -> ClinicalEncounterSummaryResponse:
    enc = aggregate.encounter
    return ClinicalEncounterSummaryResponse(
        id=enc.id,
        patient_id=enc.patient_id,
        organization_id=enc.organization_id,
        clinician_user_id=enc.clinician_user_id,
        specialty_key=enc.specialty_key,
        status=enc.status,
        locale=enc.locale,
        started_at=enc.started_at,
        ended_at=enc.ended_at,
        appointment_id=enc.appointment_id,
        version=enc.version,
    )


def encounter_detail_response(aggregate: ClinicalEncounterAggregate) -> ClinicalEncounterDetailResponse:
    return ClinicalEncounterDetailResponse(
        encounter=encounter_summary_response(aggregate),
        complaints=[
            EncounterComplaintResponse.model_validate(c.__dict__) for c in _active_complaints(aggregate)
        ],
        findings=[
            EncounterFindingResponse.model_validate(f.__dict__) for f in _active_findings(aggregate)
        ],
        question_responses=[
            EncounterQuestionResponseItem.model_validate(r.__dict__)
            for r in _active_responses(aggregate)
        ],
        final_summary=_final_summary_response(aggregate.final_summary),
    )


def _final_summary_response(
    summary: EncounterFinalSummary | None,
) -> EncounterFinalSummaryResponse | None:
    if summary is None:
        return None
    return EncounterFinalSummaryResponse(
        id=summary.id,
        encounter_id=summary.encounter_id,
        summary_version=summary.summary_version,
        summary_sections=[
            EncounterSummarySectionResponse(
                section_key=s.section_key,
                content_key=s.content_key,
                clinician_text=s.clinician_text,
            )
            for s in summary.summary_sections
        ],
        clinician_note=summary.clinician_note,
        finalized_by=summary.finalized_by,
        finalized_at=summary.finalized_at,
        created_at=summary.created_at,
    )


def sections_from_api(
    sections: list,
) -> tuple[EncounterSummarySection, ...]:
    return tuple(
        EncounterSummarySection(
            section_key=s.section_key,
            content_key=s.content_key,
            clinician_text=s.clinician_text,
        )
        for s in sections
    )


def encounter_list_response(
    items: list[ClinicalEncounterAggregate],
    *,
    total: int,
    limit: int,
    offset: int,
) -> ClinicalEncounterListResponse:
    return ClinicalEncounterListResponse(
        items=[encounter_summary_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )

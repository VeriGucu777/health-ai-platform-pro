"""Domain ↔ ORM mappers for clinical encounter aggregate (no I/O)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

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
    EncounterStatus,
    FindingType,
    QuestionAnswerType,
)
from app.infrastructure.clinical_encounter.exceptions import ClinicalEncounterMappingError
from app.infrastructure.database.models.clinical_encounter import (
    ClinicalEncounterModel,
    EncounterComplaintModel,
    EncounterFinalSummaryModel,
    EncounterFindingModel,
    EncounterQuestionResponseModel,
)


def _parse_summary_sections(raw: Any) -> tuple[EncounterSummarySection, ...]:
    if not isinstance(raw, list) or not raw:
        raise ClinicalEncounterMappingError("summary_sections must be a non-empty JSON array")
    sections: list[EncounterSummarySection] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ClinicalEncounterMappingError("summary section must be an object")
        section_key = item.get("section_key")
        if not isinstance(section_key, str):
            raise ClinicalEncounterMappingError("summary section_key required")
        content_key = item.get("content_key")
        clinician_text = item.get("clinician_text")
        sections.append(
            EncounterSummarySection(
                section_key=section_key,
                content_key=content_key if isinstance(content_key, str) else None,
                clinician_text=clinician_text if isinstance(clinician_text, str) else None,
            ),
        )
    return tuple(sections)


def summary_sections_to_json(sections: tuple[EncounterSummarySection, ...]) -> list[dict[str, str | None]]:
    return [
        {
            "section_key": section.section_key,
            "content_key": section.content_key,
            "clinician_text": section.clinician_text,
        }
        for section in sections
    ]


def encounter_model_to_domain(model: ClinicalEncounterModel) -> ClinicalEncounter:
    return ClinicalEncounter(
        id=model.id,
        patient_id=model.patient_id,
        organization_id=model.organization_id,
        clinician_user_id=model.clinician_user_id,
        specialty_key=model.specialty_key,
        status=EncounterStatus(model.status),
        locale=model.locale,
        started_at=model.started_at,
        ended_at=model.ended_at,
        appointment_id=model.appointment_id,
        engine_version_at_start=model.engine_version_at_start,
        policy_profile_id_at_start=model.policy_profile_id_at_start,
        policy_profile_version_at_start=model.policy_profile_version_at_start,
        version=model.version,
        is_active=model.is_active,
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def encounter_domain_to_model(encounter: ClinicalEncounter) -> ClinicalEncounterModel:
    return ClinicalEncounterModel(
        id=encounter.id,
        patient_id=encounter.patient_id,
        organization_id=encounter.organization_id,
        clinician_user_id=encounter.clinician_user_id,
        specialty_key=encounter.specialty_key,
        status=encounter.status.value,
        locale=encounter.locale,
        started_at=encounter.started_at,
        ended_at=encounter.ended_at,
        appointment_id=encounter.appointment_id,
        engine_version_at_start=encounter.engine_version_at_start,
        policy_profile_id_at_start=encounter.policy_profile_id_at_start,
        policy_profile_version_at_start=encounter.policy_profile_version_at_start,
        version=encounter.version,
        is_active=encounter.is_active,
        deleted_at=encounter.deleted_at,
        created_at=encounter.created_at,
        updated_at=encounter.updated_at,
    )


def complaint_model_to_domain(model: EncounterComplaintModel) -> EncounterComplaint:
    return EncounterComplaint(
        id=model.id,
        encounter_id=model.encounter_id,
        complaint_key=model.complaint_key,
        clinician_display_text=model.clinician_display_text,
        is_primary=model.is_primary,
        negated=model.negated,
        sequence_no=model.sequence_no,
        recorded_at=model.recorded_at,
        recorded_by=model.recorded_by,
        is_active=model.is_active,
        deleted_at=model.deleted_at,
    )


def complaint_domain_to_model(entity: EncounterComplaint) -> EncounterComplaintModel:
    return EncounterComplaintModel(
        id=entity.id,
        encounter_id=entity.encounter_id,
        complaint_key=entity.complaint_key,
        clinician_display_text=entity.clinician_display_text,
        is_primary=entity.is_primary,
        negated=entity.negated,
        sequence_no=entity.sequence_no,
        recorded_at=entity.recorded_at,
        recorded_by=entity.recorded_by,
        is_active=entity.is_active,
        deleted_at=entity.deleted_at,
    )


def finding_model_to_domain(model: EncounterFindingModel) -> EncounterFinding:
    return EncounterFinding(
        id=model.id,
        encounter_id=model.encounter_id,
        finding_type=FindingType(model.finding_type),
        finding_key=model.finding_key,
        value_code=model.value_code,
        value_numeric=model.value_numeric,
        unit=model.unit,
        negated=model.negated,
        onset_code=model.onset_code,
        source=ClinicalInputSource(model.source),
        sequence_no=model.sequence_no,
        recorded_at=model.recorded_at,
        recorded_by=model.recorded_by,
        is_active=model.is_active,
        deleted_at=model.deleted_at,
    )


def finding_domain_to_model(entity: EncounterFinding) -> EncounterFindingModel:
    return EncounterFindingModel(
        id=entity.id,
        encounter_id=entity.encounter_id,
        finding_type=entity.finding_type.value,
        finding_key=entity.finding_key,
        value_code=entity.value_code,
        value_numeric=entity.value_numeric,
        unit=entity.unit,
        negated=entity.negated,
        onset_code=entity.onset_code,
        source=entity.source.value,
        sequence_no=entity.sequence_no,
        recorded_at=entity.recorded_at,
        recorded_by=entity.recorded_by,
        is_active=entity.is_active,
        deleted_at=entity.deleted_at,
    )


def response_model_to_domain(model: EncounterQuestionResponseModel) -> EncounterQuestionResponse:
    return EncounterQuestionResponse(
        id=model.id,
        encounter_id=model.encounter_id,
        question_key=model.question_key,
        answer_type=QuestionAnswerType(model.answer_type),
        answer_code=model.answer_code,
        answer_numeric=model.answer_numeric,
        clinician_note=model.clinician_note,
        sequence_no=model.sequence_no,
        answered_at=model.answered_at,
        answered_by=model.answered_by,
        is_active=model.is_active,
        deleted_at=model.deleted_at,
    )


def response_domain_to_model(entity: EncounterQuestionResponse) -> EncounterQuestionResponseModel:
    return EncounterQuestionResponseModel(
        id=entity.id,
        encounter_id=entity.encounter_id,
        question_key=entity.question_key,
        answer_type=entity.answer_type.value,
        answer_code=entity.answer_code,
        answer_numeric=entity.answer_numeric,
        clinician_note=entity.clinician_note,
        sequence_no=entity.sequence_no,
        answered_at=entity.answered_at,
        answered_by=entity.answered_by,
        is_active=entity.is_active,
        deleted_at=entity.deleted_at,
    )


def final_summary_model_to_domain(model: EncounterFinalSummaryModel) -> EncounterFinalSummary:
    sections = _parse_summary_sections(model.summary_sections)
    return EncounterFinalSummary(
        id=model.id,
        encounter_id=model.encounter_id,
        summary_version=model.summary_version,
        summary_sections=sections,
        finalized_by=model.finalized_by,
        finalized_at=model.finalized_at,
        created_at=model.created_at,
        clinician_note=model.clinician_note,
    )


def final_summary_domain_to_model(entity: EncounterFinalSummary) -> EncounterFinalSummaryModel:
    return EncounterFinalSummaryModel(
        id=entity.id,
        encounter_id=entity.encounter_id,
        summary_version=entity.summary_version,
        summary_sections=summary_sections_to_json(entity.summary_sections),
        clinician_note=entity.clinician_note,
        finalized_by=entity.finalized_by,
        finalized_at=entity.finalized_at,
        created_at=entity.created_at,
    )


def build_aggregate(
    encounter: ClinicalEncounterModel,
    *,
    complaints: list[EncounterComplaintModel],
    findings: list[EncounterFindingModel],
    responses: list[EncounterQuestionResponseModel],
    final_summary: EncounterFinalSummaryModel | None,
) -> ClinicalEncounterAggregate:
    return ClinicalEncounterAggregate(
        encounter=encounter_model_to_domain(encounter),
        complaints=tuple(complaint_model_to_domain(c) for c in complaints),
        findings=tuple(finding_model_to_domain(f) for f in findings),
        question_responses=tuple(response_model_to_domain(r) for r in responses),
        final_summary=final_summary_model_to_domain(final_summary) if final_summary else None,
    )

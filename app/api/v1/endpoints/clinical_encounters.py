"""Clinical encounter HTTP API (service-backed; no clinical engine)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import ClinicalUser, get_clinical_encounter_service
from app.api.mappers.clinical_encounter import (
    encounter_detail_response,
    encounter_list_response,
    encounter_summary_response,
    sections_from_api,
)
from app.api.schemas.clinical_encounter import (
    ClinicalEncounterCreate,
    ClinicalEncounterDetailResponse,
    ClinicalEncounterListResponse,
    ClinicalEncounterSummaryResponse,
    EncounterCancelRequest,
    EncounterComplaintCreate,
    EncounterComplaintResponse,
    EncounterFinalizeRequest,
    EncounterFindingCreate,
    EncounterFindingResponse,
    EncounterQuestionResponseItem,
    EncounterQuestionResponseUpsert,
)
from app.application.services.clinical_encounter_service import ClinicalEncounterService

patient_encounters_router = APIRouter()
encounters_router = APIRouter()


def _complaint_response(aggregate, complaint_id: UUID) -> EncounterComplaintResponse:
    complaint = next(c for c in aggregate.complaints if c.id == complaint_id)
    return EncounterComplaintResponse.model_validate(complaint.__dict__)


def _finding_response(aggregate, finding_id: UUID) -> EncounterFindingResponse:
    finding = next(f for f in aggregate.findings if f.id == finding_id)
    return EncounterFindingResponse.model_validate(finding.__dict__)


def _question_response(aggregate, question_key: str) -> EncounterQuestionResponseItem:
    response = next(
        r
        for r in aggregate.question_responses
        if r.question_key == question_key and r.is_active and r.deleted_at is None
    )
    return EncounterQuestionResponseItem.model_validate(response.__dict__)


@patient_encounters_router.post(
    "/{patient_id}/encounters",
    response_model=ClinicalEncounterDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a clinical encounter for a patient",
)
async def create_clinical_encounter(
    patient_id: UUID,
    body: ClinicalEncounterCreate,
    current_user: ClinicalUser,
    service: Annotated[ClinicalEncounterService, Depends(get_clinical_encounter_service)],
) -> ClinicalEncounterDetailResponse:
    aggregate = await service.create_encounter(
        current_user.id,
        current_user.role,
        patient_id=patient_id,
        specialty_key=body.specialty_key,
        locale=body.locale,
        appointment_id=body.appointment_id,
    )
    return encounter_detail_response(aggregate)


@patient_encounters_router.get(
    "/{patient_id}/encounters",
    response_model=ClinicalEncounterListResponse,
    summary="List clinical encounters for a patient",
)
async def list_patient_clinical_encounters(
    patient_id: UUID,
    current_user: ClinicalUser,
    service: Annotated[ClinicalEncounterService, Depends(get_clinical_encounter_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
) -> ClinicalEncounterListResponse:
    items = await service.list_patient_encounters(
        current_user.id,
        current_user.role,
        patient_id=patient_id,
        offset=offset,
        limit=limit,
    )
    if status_filter is not None:
        normalized = status_filter.strip().lower()
        items = [item for item in items if item.encounter.status.value == normalized]
    return encounter_list_response(
        items,
        total=len(items),
        limit=limit,
        offset=offset,
    )


@encounters_router.get(
    "/{encounter_id}",
    response_model=ClinicalEncounterDetailResponse,
    summary="Get clinical encounter detail",
)
async def get_clinical_encounter(
    encounter_id: UUID,
    current_user: ClinicalUser,
    service: Annotated[ClinicalEncounterService, Depends(get_clinical_encounter_service)],
) -> ClinicalEncounterDetailResponse:
    aggregate = await service.get_encounter(
        current_user.id,
        current_user.role,
        encounter_id,
    )
    return encounter_detail_response(aggregate)


@encounters_router.post(
    "/{encounter_id}/complaints",
    response_model=EncounterComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add complaint to encounter",
)
async def add_encounter_complaint(
    encounter_id: UUID,
    body: EncounterComplaintCreate,
    current_user: ClinicalUser,
    service: Annotated[ClinicalEncounterService, Depends(get_clinical_encounter_service)],
) -> EncounterComplaintResponse:
    aggregate = await service.add_complaint(
        current_user.id,
        current_user.role,
        encounter_id,
        complaint_key=body.complaint_key,
        clinician_display_text=body.clinician_display_text,
        is_primary=body.is_primary,
        negated=body.negated,
    )
    complaint_id = aggregate.complaints[-1].id
    return _complaint_response(aggregate, complaint_id)


@encounters_router.post(
    "/{encounter_id}/findings",
    response_model=EncounterFindingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add finding to encounter",
)
async def add_encounter_finding(
    encounter_id: UUID,
    body: EncounterFindingCreate,
    current_user: ClinicalUser,
    service: Annotated[ClinicalEncounterService, Depends(get_clinical_encounter_service)],
) -> EncounterFindingResponse:
    aggregate = await service.add_finding(
        current_user.id,
        current_user.role,
        encounter_id,
        finding_type=body.finding_type,
        finding_key=body.finding_key,
        value_code=body.value_code,
        value_numeric=body.value_numeric,
        unit=body.unit,
        negated=body.negated,
        onset_code=body.onset_code,
        source=body.source,
    )
    finding_id = aggregate.findings[-1].id
    return _finding_response(aggregate, finding_id)


@encounters_router.put(
    "/{encounter_id}/question-responses/{question_key}",
    response_model=EncounterQuestionResponseItem,
    summary="Record or update structured question response",
)
async def upsert_encounter_question_response(
    encounter_id: UUID,
    question_key: str,
    body: EncounterQuestionResponseUpsert,
    current_user: ClinicalUser,
    service: Annotated[ClinicalEncounterService, Depends(get_clinical_encounter_service)],
) -> EncounterQuestionResponseItem:
    aggregate = await service.record_question_response(
        current_user.id,
        current_user.role,
        encounter_id,
        question_key=question_key,
        answer_type=body.answer_type,
        answer_code=body.answer_code,
        answer_numeric=body.answer_numeric,
        clinician_note=body.clinician_note,
    )
    return _question_response(aggregate, question_key)


@encounters_router.delete(
    "/{encounter_id}/complaints/{complaint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-deactivate an encounter complaint",
)
async def deactivate_encounter_complaint(
    encounter_id: UUID,
    complaint_id: UUID,
    current_user: ClinicalUser,
    service: Annotated[ClinicalEncounterService, Depends(get_clinical_encounter_service)],
) -> Response:
    await service.deactivate_complaint(
        current_user.id,
        current_user.role,
        encounter_id,
        complaint_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@encounters_router.post(
    "/{encounter_id}/finalize",
    response_model=ClinicalEncounterDetailResponse,
    summary="Finalize clinical encounter",
)
async def finalize_clinical_encounter(
    encounter_id: UUID,
    body: EncounterFinalizeRequest,
    current_user: ClinicalUser,
    service: Annotated[ClinicalEncounterService, Depends(get_clinical_encounter_service)],
) -> ClinicalEncounterDetailResponse:
    aggregate = await service.finalize_encounter(
        current_user.id,
        current_user.role,
        encounter_id,
        summary_sections=sections_from_api(body.summary_sections),
        clinician_note=body.clinician_note,
        expected_version=body.expected_version,
    )
    return encounter_detail_response(aggregate)


@encounters_router.post(
    "/{encounter_id}/cancel",
    response_model=ClinicalEncounterSummaryResponse,
    summary="Cancel clinical encounter",
)
async def cancel_clinical_encounter(
    encounter_id: UUID,
    body: EncounterCancelRequest,
    current_user: ClinicalUser,
    service: Annotated[ClinicalEncounterService, Depends(get_clinical_encounter_service)],
) -> ClinicalEncounterSummaryResponse:
    aggregate = await service.cancel_encounter(
        current_user.id,
        current_user.role,
        encounter_id,
        expected_version=body.expected_version,
    )
    return encounter_summary_response(aggregate)

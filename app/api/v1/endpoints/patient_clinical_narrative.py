"""Patient clinical narrative endpoints."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.deps import ClinicalUser, get_audit_service, get_clinical_narrative_service
from app.api.schemas.clinical_narrative import (
    PatientClinicalNarrativeRequest,
    PatientClinicalNarrativeResponse,
)
from app.application.clinical_narrative.constants import NARRATIVE_VERSION, PROMPT_VERSION
from app.application.dtos.clinical_narrative import PatientClinicalNarrativeDTO
from app.application.services.audit_service import AuditService
from app.application.services.clinical_narrative_audit_recorder import (
    record_clinical_narrative_audit_event,
)
from app.application.services.clinical_narrative_service import ClinicalNarrativeService
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditOutcome
from app.middleware.clinical_narrative_rate_limit import enforce_clinical_narrative_rate_limit

router = APIRouter()


def _response(data: PatientClinicalNarrativeDTO) -> PatientClinicalNarrativeResponse:
    return PatientClinicalNarrativeResponse.model_validate(data.model_dump())


def _audit_metadata(
    *,
    body: PatientClinicalNarrativeRequest,
    provider_kind: str,
    model_identifier: str,
    evidence_count: int,
    fallback_used: bool,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "narrative_version": NARRATIVE_VERSION,
        "prompt_version": PROMPT_VERSION,
        "evidence_count": evidence_count,
        "provider_kind": provider_kind,
        "model_identifier": model_identifier,
        "fallback_used": fallback_used,
        "max_evidence": body.max_evidence,
    }
    if body.language is not None:
        metadata["language"] = body.language
    if body.source_types:
        metadata["source_types"] = ",".join(st.value for st in body.source_types)
    if body.date_from is not None:
        metadata["date_from"] = body.date_from.isoformat()
    if body.date_to is not None:
        metadata["date_to"] = body.date_to.isoformat()
    return metadata


@router.post(
    "/{patient_id}/clinical-narrative",
    response_model=PatientClinicalNarrativeResponse,
    summary="Generate LLM clinical narrative from authorized RAG evidence",
)
async def post_patient_clinical_narrative(
    patient_id: UUID,
    body: PatientClinicalNarrativeRequest,
    request: Request,
    current_user: ClinicalUser,
    narrative_service: Annotated[ClinicalNarrativeService, Depends(get_clinical_narrative_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    _rate_limit: Annotated[None, Depends(enforce_clinical_narrative_rate_limit)],
) -> PatientClinicalNarrativeResponse:
    audit_context = build_auth_audit_context(request)
    provider_info = narrative_service.provider_info()
    try:
        result, organization_id = await narrative_service.generate_narrative(
            current_user.id,
            current_user.role,
            patient_id=patient_id,
            query=body.query,
            date_from=body.date_from,
            date_to=body.date_to,
            source_types=body.source_types,
            max_evidence=body.max_evidence,
            language=body.language,
        )
    except AppException as exc:
        await record_clinical_narrative_audit_event(
            audit_service,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            patient_id=patient_id,
            metadata={
                "narrative_version": NARRATIVE_VERSION,
                "prompt_version": PROMPT_VERSION,
                "provider_kind": provider_info.provider_kind,
                "model_identifier": provider_info.model_identifier,
                "fallback_used": False,
            },
        )
        raise

    metadata = _audit_metadata(
        body=body,
        provider_kind=provider_info.provider_kind,
        model_identifier=provider_info.model_identifier,
        evidence_count=len(result.evidence_references),
        fallback_used=result.fallback_used,
    )
    await record_clinical_narrative_audit_event(
        audit_service,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        patient_id=patient_id,
        metadata=metadata,
        organization_id=organization_id,
    )
    return _response(result)

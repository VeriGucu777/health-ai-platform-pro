"""Patient clinical retrieval endpoints."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.deps import (
    ClinicalUser,
    get_audit_service,
    get_clinical_retrieval_service,
    require_clinical_rag_enabled,
)
from app.api.schemas.clinical_retrieval import (
    PatientClinicalRetrievalRequest,
    PatientClinicalRetrievalResponse,
)
from app.application.clinical_retrieval.constants import RETRIEVAL_VERSION
from app.application.dtos.clinical_retrieval import PatientClinicalRetrievalDTO
from app.application.services.audit_service import AuditService
from app.application.services.clinical_retrieval_audit_recorder import (
    record_clinical_retrieval_audit_event,
)
from app.application.services.clinical_retrieval_service import ClinicalRetrievalService
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditOutcome

router = APIRouter()


def _response(data: PatientClinicalRetrievalDTO) -> PatientClinicalRetrievalResponse:
    return PatientClinicalRetrievalResponse.model_validate(data.model_dump())


def _audit_metadata(
    *,
    body: PatientClinicalRetrievalRequest,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "retrieval_version": RETRIEVAL_VERSION,
        "top_k": body.top_k,
    }
    if body.source_types:
        metadata["source_types"] = ",".join(st.value for st in body.source_types)
    if body.date_from is not None:
        metadata["date_from"] = body.date_from.isoformat()
    if body.date_to is not None:
        metadata["date_to"] = body.date_to.isoformat()
    return metadata


@router.post(
    "/{patient_id}/clinical-retrieval",
    response_model=PatientClinicalRetrievalResponse,
    summary="Search authorized clinical evidence (RAG retrieval v1)",
)
async def post_patient_clinical_retrieval(
    patient_id: UUID,
    body: PatientClinicalRetrievalRequest,
    request: Request,
    current_user: ClinicalUser,
    _rag_enabled: Annotated[None, Depends(require_clinical_rag_enabled)],
    retrieval_service: Annotated[ClinicalRetrievalService, Depends(get_clinical_retrieval_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PatientClinicalRetrievalResponse:
    audit_context = build_auth_audit_context(request)
    metadata = _audit_metadata(body=body)
    try:
        result, organization_id = await retrieval_service.search(
            current_user.id,
            current_user.role,
            patient_id=patient_id,
            query=body.query,
            top_k=body.top_k,
            source_types=body.source_types,
            date_from=body.date_from,
            date_to=body.date_to,
        )
    except AppException as exc:
        await record_clinical_retrieval_audit_event(
            audit_service,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            patient_id=patient_id,
            metadata=metadata,
        )
        raise

    await record_clinical_retrieval_audit_event(
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

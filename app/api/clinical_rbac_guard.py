"""Clinical RBAC guard with optional denied-access audit for in-scope routes."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.deps import get_audit_service, get_current_user
from app.application.dtos.user import UserDTO
from app.application.services.audit_service import AuditService
from app.application.services.clinical_rbac_audit_recorder import (
    record_clinical_rbac_denied_audit_event,
)
from app.domain.audit.clinical_denied_mapping import resolve_clinical_denied_audit
from app.domain.entities.user import UserRole

_CLINICAL_ROLES = frozenset({UserRole.DOCTOR, UserRole.CLINIC_ADMIN})


async def enforce_clinical_role_with_audit(
    request: Request,
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> UserDTO:
    """Allow doctor/clinic_admin; audit and deny other roles on in-scope patient routes."""
    if current_user.role in _CLINICAL_ROLES:
        return current_user

    mapping = resolve_clinical_denied_audit(request)
    if mapping is not None:
        resource_type, action = mapping
        patient_id_raw = request.path_params.get("patient_id")
        resource_id = UUID(patient_id_raw) if patient_id_raw else None
        await record_clinical_rbac_denied_audit_event(
            audit_service,
            audit_context=build_auth_audit_context(request),
            current_user=current_user,
            resource_type=resource_type,
            action=action,
            resource_id=resource_id,
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )

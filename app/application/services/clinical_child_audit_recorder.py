"""Fail-open audit helpers for clinical child resource access."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from app.application.dtos.audit_log import AuditRecordInput
from app.application.dtos.auth_audit import AuthAuditContext
from app.application.dtos.user import UserDTO
from app.core.logging import get_logger
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType

if TYPE_CHECKING:
    from app.application.services.audit_service import AuditService

ClinicalChildKind = Literal["appointment", "medical_record", "health_measurement"]

AnalyticsEndpoint = Literal["summary", "trends", "insights"]

logger = get_logger(__name__)


def _iso_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def build_list_read_metadata(
    *,
    child_kind: ClinicalChildKind,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    return {
        "child_kind": child_kind,
        "page": page,
        "page_size": page_size,
    }


def build_analytics_read_metadata(
    *,
    analytics_endpoint: AnalyticsEndpoint,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "child_kind": "health_measurement",
        "analytics_endpoint": analytics_endpoint,
    }
    if date_from is not None:
        meta["date_from"] = _iso_datetime(date_from)
    if date_to is not None:
        meta["date_to"] = _iso_datetime(date_to)
    if period is not None:
        meta["period"] = period
    return meta


def _merge_metadata(
    *,
    child_kind: ClinicalChildKind | Literal["health_measurement"],
    child_id: UUID | None,
    extra: dict[str, Any] | None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {"child_kind": child_kind}
    if child_id is not None:
        meta["child_id"] = str(child_id)
    if extra:
        meta.update(extra)
    return meta


async def record_clinical_child_audit_event(
    audit_service: AuditService | None,
    *,
    action: AuditAction,
    outcome: AuditOutcome,
    http_status: int,
    audit_context: AuthAuditContext | None,
    current_user: UserDTO,
    child_kind: ClinicalChildKind | Literal["health_measurement"],
    patient_id: UUID | None = None,
    child_id: UUID | None = None,
    organization_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist a PHI-safe clinical child audit event."""
    if audit_service is None or audit_context is None:
        return

    entry = AuditRecordInput(
        resource_type=AuditResourceType.PATIENT,
        action=action,
        outcome=outcome,
        http_status=http_status,
        actor_id=current_user.id,
        actor_role=current_user.role,
        owner_scope_id=current_user.id,
        resource_id=patient_id,
        organization_id=organization_id,
        request_id=audit_context.request_id,
        route_template=audit_context.route_template,
        client_ip_truncated=audit_context.client_ip_truncated,
        metadata=_merge_metadata(child_kind=child_kind, child_id=child_id, extra=metadata),
    )

    try:
        await audit_service.record(entry)
    except Exception:
        logger.exception(
            "Failed to persist clinical child audit event",
            extra={
                "audit_action": action.value,
                "audit_outcome": outcome.value,
                "http_status": http_status,
                "request_id": audit_context.request_id,
                "child_kind": child_kind,
            },
        )


async def record_clinical_child_read_failure(
    audit_service: AuditService | None,
    *,
    audit_context: AuthAuditContext | None,
    current_user: UserDTO,
    action: AuditAction,
    http_status: int,
    child_kind: ClinicalChildKind | Literal["health_measurement"],
    child_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Enumeration-safe failure audit (no patient resource_id)."""
    await record_clinical_child_audit_event(
        audit_service,
        action=action,
        outcome=AuditOutcome.FAILURE,
        http_status=http_status,
        audit_context=audit_context,
        current_user=current_user,
        child_kind=child_kind,
        patient_id=None,
        child_id=child_id,
        organization_id=None,
        metadata=metadata,
    )

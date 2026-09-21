"""Audit log domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.user import UserRole


@dataclass(kw_only=True)
class AuditLog:
    """Immutable-style audit record persisted append-only."""

    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    actor_id: UUID | None = None
    actor_role: UserRole | None = None
    resource_type: AuditResourceType
    resource_id: UUID | None = None
    action: AuditAction
    outcome: AuditOutcome
    http_status: int | None = None
    request_id: str | None = None
    route_template: str | None = None
    client_ip_truncated: str | None = None
    owner_scope_id: UUID | None = None
    organization_id: UUID | None = None
    metadata: dict[str, Any] | None = None

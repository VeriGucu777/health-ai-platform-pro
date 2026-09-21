"""Audit log ORM model — append-only."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.user import UserRole
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin


class AuditLogModel(Base, UUIDPrimaryKeyMixin):
    """SQLAlchemy model for append-only audit_logs."""

    __tablename__ = "audit_logs"

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    actor_role: Mapped[UserRole | None] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=32),
        nullable=True,
    )
    resource_type: Mapped[AuditResourceType] = mapped_column(
        String(64),
        nullable=False,
    )
    resource_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    action: Mapped[AuditAction] = mapped_column(String(64), nullable=False)
    outcome: Mapped[AuditOutcome] = mapped_column(String(32), nullable=False)
    http_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    route_template: Mapped[str | None] = mapped_column(String(512), nullable=True)
    client_ip_truncated: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_scope_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

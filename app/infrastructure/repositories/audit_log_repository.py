"""SQLAlchemy append-only audit log repository."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.user import UserRole
from app.domain.interfaces.audit_log_repository import AuditLogRepository as AuditLogRepositoryPort
from app.infrastructure.database.models.audit_log import AuditLogModel


class SQLAlchemyAuditLogRepository(AuditLogRepositoryPort):
    """PostgreSQL-backed append-only audit log repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, record: AuditLog) -> AuditLog:
        model = self._to_model(record)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    def _to_entity(self, model: AuditLogModel) -> AuditLog:
        actor_role = UserRole(model.actor_role) if model.actor_role is not None else None
        return AuditLog(
            id=model.id,
            occurred_at=model.occurred_at,
            actor_id=model.actor_id,
            actor_role=actor_role,
            resource_type=AuditResourceType(model.resource_type),
            resource_id=model.resource_id,
            action=AuditAction(model.action),
            outcome=AuditOutcome(model.outcome),
            http_status=model.http_status,
            request_id=model.request_id,
            route_template=model.route_template,
            client_ip_truncated=model.client_ip_truncated,
            owner_scope_id=model.owner_scope_id,
            organization_id=model.organization_id,
            metadata=model.metadata_json,
        )

    def _to_model(self, entity: AuditLog) -> AuditLogModel:
        return AuditLogModel(
            id=entity.id,
            occurred_at=entity.occurred_at,
            actor_id=entity.actor_id,
            actor_role=entity.actor_role,
            resource_type=entity.resource_type.value,
            resource_id=entity.resource_id,
            action=entity.action.value,
            outcome=entity.outcome.value,
            http_status=entity.http_status,
            request_id=entity.request_id,
            route_template=entity.route_template,
            client_ip_truncated=entity.client_ip_truncated,
            owner_scope_id=entity.owner_scope_id,
            organization_id=entity.organization_id,
            metadata_json=entity.metadata,
        )

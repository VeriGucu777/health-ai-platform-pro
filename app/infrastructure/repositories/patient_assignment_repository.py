"""SQLAlchemy patient assignment repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.patient_assignment_repository import (
    PatientAssignmentRepository as PatientAssignmentRepositoryPort,
)
from app.domain.organization.entities import PatientAssignment
from app.domain.organization.enums import AssignmentStatus
from app.infrastructure.database.models.patient_assignment import PatientAssignmentModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyPatientAssignmentRepository(
    SQLAlchemyRepository[PatientAssignmentModel, PatientAssignment],
    PatientAssignmentRepositoryPort,
):
    """PostgreSQL-backed patient assignment repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PatientAssignmentModel)

    async def list_by_patient_and_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> list[PatientAssignment]:
        stmt = (
            select(PatientAssignmentModel)
            .where(
                PatientAssignmentModel.patient_id == patient_id,
                PatientAssignmentModel.organization_id == organization_id,
            )
            .order_by(PatientAssignmentModel.assigned_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def get_active_primary_for_patient_in_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> PatientAssignment | None:
        stmt = select(PatientAssignmentModel).where(
            PatientAssignmentModel.patient_id == patient_id,
            PatientAssignmentModel.organization_id == organization_id,
            PatientAssignmentModel.status == AssignmentStatus.ACTIVE.value,
            PatientAssignmentModel.is_primary.is_(True),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_patient_and_assignee(
        self,
        patient_id: UUID,
        assignee_user_id: UUID,
    ) -> PatientAssignment | None:
        stmt = select(PatientAssignmentModel).where(
            PatientAssignmentModel.patient_id == patient_id,
            PatientAssignmentModel.assignee_user_id == assignee_user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    def _to_entity(self, model: PatientAssignmentModel) -> PatientAssignment:
        return PatientAssignment(
            id=model.id,
            organization_id=model.organization_id,
            patient_id=model.patient_id,
            assignee_user_id=model.assignee_user_id,
            is_primary=model.is_primary,
            status=AssignmentStatus(model.status),
            assigned_at=model.assigned_at,
            ended_at=model.ended_at,
            assigned_by_user_id=model.assigned_by_user_id,
        )

    def _to_model(self, entity: PatientAssignment) -> PatientAssignmentModel:
        return PatientAssignmentModel(
            id=entity.id,
            organization_id=entity.organization_id,
            patient_id=entity.patient_id,
            assignee_user_id=entity.assignee_user_id,
            is_primary=entity.is_primary,
            status=entity.status,
            assigned_at=entity.assigned_at,
            ended_at=entity.ended_at,
            assigned_by_user_id=entity.assigned_by_user_id,
        )

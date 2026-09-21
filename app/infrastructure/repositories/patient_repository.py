"""SQLAlchemy patient repository."""

from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.domain.entities.patient import Patient
from app.domain.patient.errors import PatientHardDeleteForbiddenError
from app.domain.interfaces.patient_repository import PatientRepository as PatientRepositoryPort
from app.domain.organization.enums import AssignmentStatus
from app.infrastructure.database.models.patient import PatientModel
from app.infrastructure.database.models.patient_assignment import PatientAssignmentModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyPatientRepository(
    SQLAlchemyRepository[PatientModel, Patient],
    PatientRepositoryPort,
):
    """PostgreSQL-backed patient repository with owner scoping."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PatientModel)

    async def get_by_id_and_owner(self, patient_id: UUID, owner_id: UUID) -> Patient | None:
        stmt = select(PatientModel).where(
            PatientModel.id == patient_id,
            PatientModel.owner_id == owner_id,
            PatientModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        stmt = (
            select(PatientModel)
            .where(PatientModel.owner_id == owner_id, PatientModel.is_active.is_(True))
            .order_by(PatientModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def count_by_owner(self, owner_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(PatientModel)
            .where(PatientModel.owner_id == owner_id, PatientModel.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_visible_to_doctor(
        self,
        doctor_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        stmt = (
            self._doctor_visible_patients_select(doctor_id)
            .order_by(PatientModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().unique().all()]

    async def count_visible_to_doctor(self, doctor_id: UUID) -> int:
        subq = self._doctor_visible_patients_select(doctor_id).subquery()
        stmt = select(func.count()).select_from(subq)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_by_organization_ids(
        self,
        organization_ids: list[UUID],
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        if not organization_ids:
            return []
        stmt = (
            select(PatientModel)
            .where(
                PatientModel.organization_id.in_(organization_ids),
                PatientModel.is_active.is_(True),
            )
            .order_by(PatientModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def count_by_organization_ids(self, organization_ids: list[UUID]) -> int:
        if not organization_ids:
            return 0
        stmt = (
            select(func.count())
            .select_from(PatientModel)
            .where(
                PatientModel.organization_id.in_(organization_ids),
                PatientModel.is_active.is_(True),
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    def _doctor_visible_patients_select(self, doctor_id: UUID):
        assignment = aliased(PatientAssignmentModel)
        active_assignment = and_(
            assignment.patient_id == PatientModel.id,
            assignment.assignee_user_id == doctor_id,
            assignment.status == AssignmentStatus.ACTIVE.value,
            assignment.ended_at.is_(None),
        )
        return (
            select(PatientModel)
            .outerjoin(assignment, active_assignment)
            .where(
                PatientModel.is_active.is_(True),
                or_(
                    PatientModel.owner_id == doctor_id,
                    assignment.id.isnot(None),
                ),
            )
        )

    async def delete(self, entity_id: UUID) -> bool:
        """Hard delete is forbidden; patients are soft-deactivated via the API."""
        raise PatientHardDeleteForbiddenError(f"Refusing hard delete for patient {entity_id}")

    def _to_entity(self, model: PatientModel) -> Patient:
        return Patient(
            id=model.id,
            owner_id=model.owner_id,
            organization_id=model.organization_id,
            first_name=model.first_name,
            last_name=model.last_name,
            date_of_birth=model.date_of_birth,
            gender=model.gender,
            phone=model.phone,
            notes=model.notes,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Patient) -> PatientModel:
        return PatientModel(
            id=entity.id,
            owner_id=entity.owner_id,
            organization_id=entity.organization_id,
            first_name=entity.first_name,
            last_name=entity.last_name,
            date_of_birth=entity.date_of_birth,
            gender=entity.gender,
            phone=entity.phone,
            notes=entity.notes,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

"""SQLAlchemy appointment repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.appointment import Appointment
from app.domain.interfaces.appointment_repository import (
    AppointmentRepository as AppointmentRepositoryPort,
)
from app.infrastructure.database.models.appointment import AppointmentModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyAppointmentRepository(
    SQLAlchemyRepository[AppointmentModel, Appointment],
    AppointmentRepositoryPort,
):
    """PostgreSQL-backed appointment repository with owner scoping."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AppointmentModel)

    async def get_by_id_and_owner(
        self,
        appointment_id: UUID,
        owner_id: UUID,
    ) -> Appointment | None:
        stmt = select(AppointmentModel).where(
            AppointmentModel.id == appointment_id,
            AppointmentModel.owner_id == owner_id,
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
        patient_id: UUID | None = None,
    ) -> list[Appointment]:
        stmt = select(AppointmentModel).where(AppointmentModel.owner_id == owner_id)
        if patient_id is not None:
            stmt = stmt.where(AppointmentModel.patient_id == patient_id)
        stmt = stmt.order_by(AppointmentModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def count_by_owner(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(AppointmentModel)
            .where(AppointmentModel.owner_id == owner_id)
        )
        if patient_id is not None:
            stmt = stmt.where(AppointmentModel.patient_id == patient_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_by_patient_ids(
        self,
        patient_ids: list[UUID],
        *,
        offset: int = 0,
        limit: int = 100,
        patient_id: UUID | None = None,
    ) -> list[Appointment]:
        if not patient_ids:
            return []
        ids = [patient_id] if patient_id is not None else patient_ids
        if patient_id is not None and patient_id not in patient_ids:
            return []
        stmt = (
            select(AppointmentModel)
            .where(AppointmentModel.patient_id.in_(ids))
            .order_by(AppointmentModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def count_by_patient_ids(
        self,
        patient_ids: list[UUID],
        *,
        patient_id: UUID | None = None,
    ) -> int:
        if not patient_ids:
            return 0
        ids = [patient_id] if patient_id is not None else patient_ids
        if patient_id is not None and patient_id not in patient_ids:
            return 0
        stmt = (
            select(func.count())
            .select_from(AppointmentModel)
            .where(AppointmentModel.patient_id.in_(ids))
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    def _to_entity(self, model: AppointmentModel) -> Appointment:
        return Appointment(
            id=model.id,
            owner_id=model.owner_id,
            patient_id=model.patient_id,
            appointment_date=model.appointment_date,
            appointment_type=model.appointment_type,
            status=model.status,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Appointment) -> AppointmentModel:
        return AppointmentModel(
            id=entity.id,
            owner_id=entity.owner_id,
            patient_id=entity.patient_id,
            appointment_date=entity.appointment_date,
            appointment_type=entity.appointment_type,
            status=entity.status,
            notes=entity.notes,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

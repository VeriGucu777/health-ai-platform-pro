"""SQLAlchemy medical record repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.medical_record import MedicalRecord
from app.domain.interfaces.medical_record_repository import (
    MedicalRecordRepository as MedicalRecordRepositoryPort,
)
from app.infrastructure.database.models.medical_record import MedicalRecordModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyMedicalRecordRepository(
    SQLAlchemyRepository[MedicalRecordModel, MedicalRecord],
    MedicalRecordRepositoryPort,
):
    """PostgreSQL-backed medical record repository with owner scoping."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MedicalRecordModel)

    async def get_by_id_and_owner(
        self,
        medical_record_id: UUID,
        owner_id: UUID,
    ) -> MedicalRecord | None:
        stmt = select(MedicalRecordModel).where(
            MedicalRecordModel.id == medical_record_id,
            MedicalRecordModel.owner_id == owner_id,
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
        record_type: str | None = None,
    ) -> list[MedicalRecord]:
        stmt = select(MedicalRecordModel).where(MedicalRecordModel.owner_id == owner_id)
        if patient_id is not None:
            stmt = stmt.where(MedicalRecordModel.patient_id == patient_id)
        if record_type is not None:
            stmt = stmt.where(MedicalRecordModel.record_type == record_type)
        stmt = stmt.order_by(MedicalRecordModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def count_by_owner(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID | None = None,
        record_type: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(MedicalRecordModel)
            .where(MedicalRecordModel.owner_id == owner_id)
        )
        if patient_id is not None:
            stmt = stmt.where(MedicalRecordModel.patient_id == patient_id)
        if record_type is not None:
            stmt = stmt.where(MedicalRecordModel.record_type == record_type)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    def _to_entity(self, model: MedicalRecordModel) -> MedicalRecord:
        return MedicalRecord(
            id=model.id,
            owner_id=model.owner_id,
            patient_id=model.patient_id,
            record_date=model.record_date,
            record_type=model.record_type,
            title=model.title,
            description=model.description,
            diagnosis=model.diagnosis,
            treatment=model.treatment,
            medications=model.medications,
            doctor_name=model.doctor_name,
            hospital_name=model.hospital_name,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: MedicalRecord) -> MedicalRecordModel:
        return MedicalRecordModel(
            id=entity.id,
            owner_id=entity.owner_id,
            patient_id=entity.patient_id,
            record_date=entity.record_date,
            record_type=entity.record_type,
            title=entity.title,
            description=entity.description,
            diagnosis=entity.diagnosis,
            treatment=entity.treatment,
            medications=entity.medications,
            doctor_name=entity.doctor_name,
            hospital_name=entity.hospital_name,
            notes=entity.notes,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

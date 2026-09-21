"""SQLAlchemy patient consent repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.consent.entities import PatientConsent
from app.domain.consent.enums import ConsentSource, ConsentStatus, ConsentType
from app.domain.interfaces.patient_consent_repository import (
    PatientConsentRepository as PatientConsentRepositoryPort,
)
from app.infrastructure.database.models.patient_consent import PatientConsentModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyPatientConsentRepository(
    SQLAlchemyRepository[PatientConsentModel, PatientConsent],
    PatientConsentRepositoryPort,
):
    """PostgreSQL-backed patient consent repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PatientConsentModel)

    async def list_by_patient_and_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> list[PatientConsent]:
        stmt = (
            select(PatientConsentModel)
            .where(
                PatientConsentModel.patient_id == patient_id,
                PatientConsentModel.organization_id == organization_id,
            )
            .order_by(PatientConsentModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def get_active_granted(
        self,
        patient_id: UUID,
        organization_id: UUID,
        consent_type: ConsentType,
    ) -> PatientConsent | None:
        stmt = select(PatientConsentModel).where(
            PatientConsentModel.patient_id == patient_id,
            PatientConsentModel.organization_id == organization_id,
            PatientConsentModel.consent_type == consent_type.value,
            PatientConsentModel.status == ConsentStatus.GRANTED.value,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_max_version(
        self,
        patient_id: UUID,
        organization_id: UUID,
        consent_type: ConsentType,
    ) -> int:
        stmt = select(func.max(PatientConsentModel.version)).where(
            PatientConsentModel.patient_id == patient_id,
            PatientConsentModel.organization_id == organization_id,
            PatientConsentModel.consent_type == consent_type.value,
        )
        result = await self._session.execute(stmt)
        value = result.scalar_one_or_none()
        return int(value or 0)

    def _to_entity(self, model: PatientConsentModel) -> PatientConsent:
        return PatientConsent(
            id=model.id,
            patient_id=model.patient_id,
            organization_id=model.organization_id,
            consent_type=ConsentType(model.consent_type),
            status=ConsentStatus(model.status),
            granted_at=model.granted_at,
            revoked_at=model.revoked_at,
            recorded_by_user_id=model.recorded_by_user_id,
            version=model.version,
            source=ConsentSource(model.source),
            created_at=model.created_at,
        )

    def _to_model(self, entity: PatientConsent) -> PatientConsentModel:
        return PatientConsentModel(
            id=entity.id,
            patient_id=entity.patient_id,
            organization_id=entity.organization_id,
            consent_type=entity.consent_type.value,
            status=entity.status.value,
            granted_at=entity.granted_at,
            revoked_at=entity.revoked_at,
            recorded_by_user_id=entity.recorded_by_user_id,
            version=entity.version,
            source=entity.source.value,
            created_at=entity.created_at,
        )

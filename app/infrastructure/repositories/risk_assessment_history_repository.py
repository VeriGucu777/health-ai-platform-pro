"""SQLAlchemy append-only risk assessment history repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository
from app.domain.risk.enums import RiskAssessmentType
from app.infrastructure.database.models.risk_assessment_history import RiskAssessmentHistoryModel


class SQLAlchemyRiskAssessmentHistoryRepository(RiskAssessmentHistoryRepository):
    """PostgreSQL-backed risk assessment history (append + ops soft-deactivate)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, entry: RiskAssessmentHistory) -> RiskAssessmentHistory:
        model = self._to_model(entry)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(
        self,
        row_id: UUID,
        *,
        include_inactive: bool = False,
    ) -> RiskAssessmentHistory | None:
        stmt = select(RiskAssessmentHistoryModel).where(RiskAssessmentHistoryModel.id == row_id)
        stmt = self._apply_active_filter(stmt, include_inactive)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, entry: RiskAssessmentHistory) -> RiskAssessmentHistory:
        model = self._to_model(entry)
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return self._to_entity(merged)

    async def list_by_patient(
        self,
        patient_id: UUID,
        *,
        assessment_type: RiskAssessmentType | None = None,
        evaluated_at_from: datetime | None = None,
        evaluated_at_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
        include_inactive: bool = False,
    ) -> list[RiskAssessmentHistory]:
        stmt = self._filtered_stmt(
            patient_id,
            assessment_type=assessment_type,
            evaluated_at_from=evaluated_at_from,
            evaluated_at_to=evaluated_at_to,
            include_inactive=include_inactive,
        )
        stmt = stmt.order_by(
            RiskAssessmentHistoryModel.evaluated_at.desc(),
            RiskAssessmentHistoryModel.created_at.desc(),
        ).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def count_by_patient(
        self,
        patient_id: UUID,
        *,
        assessment_type: RiskAssessmentType | None = None,
        evaluated_at_from: datetime | None = None,
        evaluated_at_to: datetime | None = None,
        include_inactive: bool = False,
    ) -> int:
        base = self._filtered_stmt(
            patient_id,
            assessment_type=assessment_type,
            evaluated_at_from=evaluated_at_from,
            evaluated_at_to=evaluated_at_to,
            include_inactive=include_inactive,
        )
        stmt = select(func.count()).select_from(base.subquery())
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    def _filtered_stmt(
        self,
        patient_id: UUID,
        *,
        assessment_type: RiskAssessmentType | None,
        evaluated_at_from: datetime | None,
        evaluated_at_to: datetime | None,
        include_inactive: bool,
    ):
        stmt = select(RiskAssessmentHistoryModel).where(
            RiskAssessmentHistoryModel.patient_id == patient_id,
        )
        stmt = self._apply_active_filter(stmt, include_inactive)
        if assessment_type is not None:
            stmt = stmt.where(
                RiskAssessmentHistoryModel.assessment_type == assessment_type.value,
            )
        if evaluated_at_from is not None:
            stmt = stmt.where(RiskAssessmentHistoryModel.evaluated_at >= evaluated_at_from)
        if evaluated_at_to is not None:
            stmt = stmt.where(RiskAssessmentHistoryModel.evaluated_at <= evaluated_at_to)
        return stmt

    @staticmethod
    def _apply_active_filter(stmt, include_inactive: bool):
        if not include_inactive:
            stmt = stmt.where(RiskAssessmentHistoryModel.is_active.is_(True))
        return stmt

    @staticmethod
    def _to_entity(model: RiskAssessmentHistoryModel) -> RiskAssessmentHistory:
        return RiskAssessmentHistory(
            id=model.id,
            patient_id=model.patient_id,
            organization_id=model.organization_id,
            assessment_type=RiskAssessmentType(model.assessment_type),
            assessment_status=model.assessment_status,
            risk_level=model.risk_level,
            score=model.score,
            probability=model.probability,
            model_kind=model.model_kind,
            model_version=model.model_version,
            evaluated_by_user_id=model.evaluated_by_user_id,
            evaluated_at=model.evaluated_at,
            result_snapshot=model.result_snapshot,
            is_active=model.is_active,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_model(entry: RiskAssessmentHistory) -> RiskAssessmentHistoryModel:
        return RiskAssessmentHistoryModel(
            id=entry.id,
            patient_id=entry.patient_id,
            organization_id=entry.organization_id,
            assessment_type=entry.assessment_type.value,
            assessment_status=entry.assessment_status,
            risk_level=entry.risk_level,
            score=entry.score,
            probability=entry.probability,
            model_kind=entry.model_kind,
            model_version=entry.model_version,
            evaluated_by_user_id=entry.evaluated_by_user_id,
            evaluated_at=entry.evaluated_at,
            result_snapshot=entry.result_snapshot,
            is_active=entry.is_active,
            deleted_at=entry.deleted_at,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

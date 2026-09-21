"""Risk assessment history DTOs."""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.risk.enums import RiskAssessmentType


class RiskAssessmentHistoryDTO(BaseSchema):
    """One immutable risk assessment snapshot."""

    id: UUID
    patient_id: UUID
    organization_id: UUID | None = None
    assessment_type: RiskAssessmentType
    assessment_status: str
    risk_level: str | None = None
    score: float | None = None
    probability: float | None = None
    model_kind: str
    model_version: str
    evaluated_by_user_id: UUID
    evaluated_at: datetime
    result_snapshot: dict[str, Any] | None = None
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: RiskAssessmentHistory) -> "RiskAssessmentHistoryDTO":
        return cls(
            id=entity.id,
            patient_id=entity.patient_id,
            organization_id=entity.organization_id,
            assessment_type=entity.assessment_type,
            assessment_status=entity.assessment_status,
            risk_level=entity.risk_level,
            score=entity.score,
            probability=entity.probability,
            model_kind=entity.model_kind,
            model_version=entity.model_version,
            evaluated_by_user_id=entity.evaluated_by_user_id,
            evaluated_at=entity.evaluated_at,
            result_snapshot=entity.result_snapshot,
            created_at=entity.created_at,
        )


class RiskAssessmentHistoryListDTO(BaseSchema):
    """Paginated risk assessment history."""

    items: list[RiskAssessmentHistoryDTO]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(
        cls,
        items: list[RiskAssessmentHistoryDTO],
        *,
        total: int,
        page: int,
        page_size: int,
    ) -> "RiskAssessmentHistoryListDTO":
        pages = max(1, (total + page_size - 1) // page_size) if page_size else 1
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

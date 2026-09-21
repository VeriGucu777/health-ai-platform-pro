"""Risk assessment history API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.risk.enums import RiskAssessmentType


class RiskAssessmentHistoryResponse(BaseModel):
    """Immutable risk assessment history item."""

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

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentHistoryListResponse(BaseModel):
    """Paginated risk assessment history."""

    items: list[RiskAssessmentHistoryResponse]
    total: int
    page: int
    page_size: int
    pages: int


class RiskAssessmentHistoryListQuery(BaseModel):
    """Validated list filters (query params composed in router)."""

    assessment_type: RiskAssessmentType | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

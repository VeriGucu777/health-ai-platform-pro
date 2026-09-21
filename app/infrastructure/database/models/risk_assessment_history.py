"""Risk assessment history ORM model — append-only."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RiskAssessmentHistoryModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """SQLAlchemy model for risk_assessment_history."""

    __tablename__ = "risk_assessment_history"

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assessment_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    assessment_status: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    result_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

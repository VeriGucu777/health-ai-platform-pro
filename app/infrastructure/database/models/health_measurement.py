"""Health measurement SQLAlchemy ORM model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class HealthMeasurementModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persistent health measurement linked to a patient and user."""

    __tablename__ = "health_measurements"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    blood_glucose: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    glucose_context: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    systolic_pressure: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diastolic_pressure: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    insulin_units: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    meal_context: Mapped[str | None] = mapped_column(String(50), nullable=True)
    exercise_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

"""Appointment ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AppointmentModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """SQLAlchemy model for the appointments table."""

    __tablename__ = "appointments"

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
    appointment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    appointment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

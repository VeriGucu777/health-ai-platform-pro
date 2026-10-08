"""Clinical encounter persistence models (schema only; no repository in Phase 1C.1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClinicalEncounterModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """In-clinic encounter session (aggregate root persistence)."""

    __tablename__ = "clinical_encounters"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_clinical_encounters_version_gte_1"),
        Index(
            "uq_clinical_encounters_one_active_per_patient_org",
            "patient_id",
            "organization_id",
            unique=True,
            postgresql_where=text(
                "status = 'active' AND is_active = true AND deleted_at IS NULL",
            ),
        ),
        Index(
            "uq_clinical_encounters_appointment_id",
            "appointment_id",
            unique=True,
            postgresql_where=text("appointment_id IS NOT NULL"),
        ),
        Index("ix_clinical_encounters_patient_started", "patient_id", "started_at"),
        Index("ix_clinical_encounters_org_started", "organization_id", "started_at"),
        Index("ix_clinical_encounters_clinician_status", "clinician_user_id", "status"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    clinician_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    specialty_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    engine_version_at_start: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_profile_id_at_start: Mapped[str | None] = mapped_column(String(128), nullable=True)
    policy_profile_version_at_start: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EncounterComplaintModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Chief/additional complaint rows for an encounter."""

    __tablename__ = "encounter_complaints"
    __table_args__ = (
        CheckConstraint("sequence_no > 0", name="ck_encounter_complaints_sequence_positive"),
        CheckConstraint(
            "complaint_key IS NOT NULL OR clinician_display_text IS NOT NULL",
            name="ck_encounter_complaints_key_or_text",
        ),
        Index(
            "uq_encounter_complaints_one_primary_active",
            "encounter_id",
            unique=True,
            postgresql_where=text(
                "is_primary = true AND is_active = true AND deleted_at IS NULL",
            ),
        ),
        Index(
            "uq_encounter_complaints_encounter_sequence_active",
            "encounter_id",
            "sequence_no",
            unique=True,
            postgresql_where=text("is_active = true AND deleted_at IS NULL"),
        ),
        Index("ix_encounter_complaints_encounter_recorded", "encounter_id", "recorded_at"),
    )

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    complaint_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    clinician_display_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    negated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EncounterFindingModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured finding captured during an encounter."""

    __tablename__ = "encounter_findings"
    __table_args__ = (
        CheckConstraint("sequence_no > 0", name="ck_encounter_findings_sequence_positive"),
        Index(
            "uq_encounter_findings_encounter_sequence_active",
            "encounter_id",
            "sequence_no",
            unique=True,
            postgresql_where=text("is_active = true AND deleted_at IS NULL"),
        ),
        Index("ix_encounter_findings_encounter_recorded", "encounter_id", "recorded_at"),
    )

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    finding_key: Mapped[str] = mapped_column(String(128), nullable=False)
    value_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    negated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    onset_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EncounterQuestionResponseModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured question response (machine keys; optional clinician note)."""

    __tablename__ = "encounter_question_responses"
    __table_args__ = (
        CheckConstraint("sequence_no > 0", name="ck_encounter_question_responses_sequence_positive"),
        Index(
            "uq_encounter_question_responses_active_key",
            "encounter_id",
            "question_key",
            unique=True,
            postgresql_where=text("is_active = true AND deleted_at IS NULL"),
        ),
        Index("ix_encounter_question_responses_encounter_answered", "encounter_id", "answered_at"),
    )

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    question_key: Mapped[str] = mapped_column(String(128), nullable=False)
    answer_type: Mapped[str] = mapped_column(String(32), nullable=False)
    answer_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    answer_numeric: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    clinician_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    answered_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EncounterFinalSummaryModel(Base, UUIDPrimaryKeyMixin):
    """Immutable clinician final summary (one row per finalized encounter)."""

    __tablename__ = "encounter_final_summaries"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    summary_version: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_sections: Mapped[dict] = mapped_column(JSONB, nullable=False)
    clinician_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    finalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

"""create clinical encounter persistence shell and nullable encounter links

Revision ID: t9u0v1w2x3y4
Revises: s8t9u0v1w2x3
Create Date: 2026-10-08 10:55:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "t9u0v1w2x3y4"
down_revision: Union[str, None] = "s8t9u0v1w2x3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinical_encounters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinician_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specialty_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("engine_version_at_start", sa.String(length=64), nullable=True),
        sa.Column("policy_profile_id_at_start", sa.String(length=128), nullable=True),
        sa.Column("policy_profile_version_at_start", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("version >= 1", name="ck_clinical_encounters_version_gte_1"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["clinician_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinical_encounters_patient_id", "clinical_encounters", ["patient_id"])
    op.create_index(
        "ix_clinical_encounters_organization_id",
        "clinical_encounters",
        ["organization_id"],
    )
    op.create_index(
        "ix_clinical_encounters_clinician_user_id",
        "clinical_encounters",
        ["clinician_user_id"],
    )
    op.create_index("ix_clinical_encounters_status", "clinical_encounters", ["status"])
    op.create_index(
        "ix_clinical_encounters_patient_started",
        "clinical_encounters",
        ["patient_id", "started_at"],
    )
    op.create_index(
        "ix_clinical_encounters_org_started",
        "clinical_encounters",
        ["organization_id", "started_at"],
    )
    op.create_index(
        "ix_clinical_encounters_clinician_status",
        "clinical_encounters",
        ["clinician_user_id", "status"],
    )
    op.create_index(
        "uq_clinical_encounters_one_active_per_patient_org",
        "clinical_encounters",
        ["patient_id", "organization_id"],
        unique=True,
        postgresql_where=sa.text(
            "status = 'active' AND is_active = true AND deleted_at IS NULL",
        ),
    )
    op.create_index(
        "uq_clinical_encounters_appointment_id",
        "clinical_encounters",
        ["appointment_id"],
        unique=True,
        postgresql_where=sa.text("appointment_id IS NOT NULL"),
    )

    op.create_table(
        "encounter_complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("complaint_key", sa.String(length=128), nullable=True),
        sa.Column("clinician_display_text", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("negated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("sequence_no > 0", name="ck_encounter_complaints_sequence_positive"),
        sa.CheckConstraint(
            "complaint_key IS NOT NULL OR clinician_display_text IS NOT NULL",
            name="ck_encounter_complaints_key_or_text",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["clinical_encounters.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_encounter_complaints_encounter_id", "encounter_complaints", ["encounter_id"])
    op.create_index(
        "ix_encounter_complaints_encounter_recorded",
        "encounter_complaints",
        ["encounter_id", "recorded_at"],
    )
    op.create_index(
        "uq_encounter_complaints_one_primary_active",
        "encounter_complaints",
        ["encounter_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_primary = true AND is_active = true AND deleted_at IS NULL",
        ),
    )
    op.create_index(
        "uq_encounter_complaints_encounter_sequence_active",
        "encounter_complaints",
        ["encounter_id", "sequence_no"],
        unique=True,
        postgresql_where=sa.text("is_active = true AND deleted_at IS NULL"),
    )

    op.create_table(
        "encounter_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_type", sa.String(length=32), nullable=False),
        sa.Column("finding_key", sa.String(length=128), nullable=False),
        sa.Column("value_code", sa.String(length=128), nullable=True),
        sa.Column("value_numeric", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("negated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("onset_code", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("sequence_no > 0", name="ck_encounter_findings_sequence_positive"),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["clinical_encounters.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_encounter_findings_encounter_id", "encounter_findings", ["encounter_id"])
    op.create_index(
        "ix_encounter_findings_encounter_recorded",
        "encounter_findings",
        ["encounter_id", "recorded_at"],
    )
    op.create_index(
        "uq_encounter_findings_encounter_sequence_active",
        "encounter_findings",
        ["encounter_id", "sequence_no"],
        unique=True,
        postgresql_where=sa.text("is_active = true AND deleted_at IS NULL"),
    )

    op.create_table(
        "encounter_question_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_key", sa.String(length=128), nullable=False),
        sa.Column("answer_type", sa.String(length=32), nullable=False),
        sa.Column("answer_code", sa.String(length=128), nullable=True),
        sa.Column("answer_numeric", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("clinician_note", sa.Text(), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "sequence_no > 0",
            name="ck_encounter_question_responses_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["clinical_encounters.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["answered_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_encounter_question_responses_encounter_id",
        "encounter_question_responses",
        ["encounter_id"],
    )
    op.create_index(
        "ix_encounter_question_responses_encounter_answered",
        "encounter_question_responses",
        ["encounter_id", "answered_at"],
    )
    op.create_index(
        "uq_encounter_question_responses_active_key",
        "encounter_question_responses",
        ["encounter_id", "question_key"],
        unique=True,
        postgresql_where=sa.text("is_active = true AND deleted_at IS NULL"),
    )

    op.create_table(
        "encounter_final_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_version", sa.Integer(), nullable=False),
        sa.Column("summary_sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("clinician_note", sa.Text(), nullable=True),
        sa.Column("finalized_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["clinical_encounters.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["finalized_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("encounter_id", name="uq_encounter_final_summaries_encounter_id"),
    )

    op.add_column(
        "health_measurements",
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_health_measurements_encounter_id_clinical_encounters",
        "health_measurements",
        "clinical_encounters",
        ["encounter_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_health_measurements_encounter_id",
        "health_measurements",
        ["encounter_id"],
    )

    op.add_column(
        "medical_records",
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_medical_records_encounter_id_clinical_encounters",
        "medical_records",
        "clinical_encounters",
        ["encounter_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_medical_records_encounter_id", "medical_records", ["encounter_id"])


def downgrade() -> None:
    op.drop_index("ix_medical_records_encounter_id", table_name="medical_records")
    op.drop_constraint(
        "fk_medical_records_encounter_id_clinical_encounters",
        "medical_records",
        type_="foreignkey",
    )
    op.drop_column("medical_records", "encounter_id")

    op.drop_index("ix_health_measurements_encounter_id", table_name="health_measurements")
    op.drop_constraint(
        "fk_health_measurements_encounter_id_clinical_encounters",
        "health_measurements",
        type_="foreignkey",
    )
    op.drop_column("health_measurements", "encounter_id")

    op.drop_table("encounter_final_summaries")
    op.drop_index(
        "uq_encounter_question_responses_active_key",
        table_name="encounter_question_responses",
    )
    op.drop_index(
        "ix_encounter_question_responses_encounter_answered",
        table_name="encounter_question_responses",
    )
    op.drop_index(
        "ix_encounter_question_responses_encounter_id",
        table_name="encounter_question_responses",
    )
    op.drop_table("encounter_question_responses")

    op.drop_index(
        "uq_encounter_findings_encounter_sequence_active",
        table_name="encounter_findings",
    )
    op.drop_index("ix_encounter_findings_encounter_recorded", table_name="encounter_findings")
    op.drop_index("ix_encounter_findings_encounter_id", table_name="encounter_findings")
    op.drop_table("encounter_findings")

    op.drop_index(
        "uq_encounter_complaints_encounter_sequence_active",
        table_name="encounter_complaints",
    )
    op.drop_index(
        "uq_encounter_complaints_one_primary_active",
        table_name="encounter_complaints",
    )
    op.drop_index("ix_encounter_complaints_encounter_recorded", table_name="encounter_complaints")
    op.drop_index("ix_encounter_complaints_encounter_id", table_name="encounter_complaints")
    op.drop_table("encounter_complaints")

    op.drop_index("uq_clinical_encounters_appointment_id", table_name="clinical_encounters")
    op.drop_index(
        "uq_clinical_encounters_one_active_per_patient_org",
        table_name="clinical_encounters",
    )
    op.drop_index("ix_clinical_encounters_clinician_status", table_name="clinical_encounters")
    op.drop_index("ix_clinical_encounters_org_started", table_name="clinical_encounters")
    op.drop_index("ix_clinical_encounters_patient_started", table_name="clinical_encounters")
    op.drop_index("ix_clinical_encounters_status", table_name="clinical_encounters")
    op.drop_index("ix_clinical_encounters_clinician_user_id", table_name="clinical_encounters")
    op.drop_index("ix_clinical_encounters_organization_id", table_name="clinical_encounters")
    op.drop_index("ix_clinical_encounters_patient_id", table_name="clinical_encounters")
    op.drop_table("clinical_encounters")

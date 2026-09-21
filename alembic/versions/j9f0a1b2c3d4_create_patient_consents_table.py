"""create patient_consents table

Revision ID: j9f0a1b2c3d4
Revises: i8e9f0a1b2c3
Create Date: 2026-09-21 08:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "j9f0a1b2c3d4"
down_revision: Union[str, None] = "i8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patient_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_patient_consents_patient_org",
        "patient_consents",
        ["patient_id", "organization_id"],
        unique=False,
    )
    op.create_index(
        "uq_patient_consents_active_granted",
        "patient_consents",
        ["patient_id", "organization_id", "consent_type"],
        unique=True,
        postgresql_where=sa.text("status = 'granted'"),
    )


def downgrade() -> None:
    op.drop_index("uq_patient_consents_active_granted", table_name="patient_consents")
    op.drop_index("ix_patient_consents_patient_org", table_name="patient_consents")
    op.drop_table("patient_consents")

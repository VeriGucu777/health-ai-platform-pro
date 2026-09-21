"""create risk_assessment_history table

Revision ID: k0a1b2c3d4e5
Revises: j9f0a1b2c3d4
Create Date: 2026-09-21 10:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "k0a1b2c3d4e5"
down_revision: Union[str, None] = "j9f0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_assessment_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assessment_type", sa.String(length=32), nullable=False),
        sa.Column("assessment_status", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("model_kind", sa.String(length=32), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("evaluated_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("result_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["evaluated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_risk_assessment_history_patient_id",
        "risk_assessment_history",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        "ix_risk_assessment_history_org_id",
        "risk_assessment_history",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_risk_assessment_history_type",
        "risk_assessment_history",
        ["assessment_type"],
        unique=False,
    )
    op.create_index(
        "ix_risk_assessment_history_evaluated_at",
        "risk_assessment_history",
        ["evaluated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_risk_assessment_history_evaluated_at", table_name="risk_assessment_history")
    op.drop_index("ix_risk_assessment_history_type", table_name="risk_assessment_history")
    op.drop_index("ix_risk_assessment_history_org_id", table_name="risk_assessment_history")
    op.drop_index("ix_risk_assessment_history_patient_id", table_name="risk_assessment_history")
    op.drop_table("risk_assessment_history")

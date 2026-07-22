"""create health measurements table

Revision ID: f5b6c7d8e9f0
Revises: e4a5b6c7d8e9
Create Date: 2026-07-22 13:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f5b6c7d8e9f0"
down_revision: Union[str, None] = "e4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "health_measurements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blood_glucose", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("glucose_context", sa.String(length=50), nullable=True),
        sa.Column("systolic_pressure", sa.Integer(), nullable=True),
        sa.Column("diastolic_pressure", sa.Integer(), nullable=True),
        sa.Column("heart_rate", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("insulin_units", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("meal_context", sa.String(length=50), nullable=True),
        sa.Column("exercise_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_health_measurements_owner_id"),
        "health_measurements",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_health_measurements_patient_id"),
        "health_measurements",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_health_measurements_measured_at"),
        "health_measurements",
        ["measured_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_health_measurements_glucose_context"),
        "health_measurements",
        ["glucose_context"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_health_measurements_glucose_context"), table_name="health_measurements")
    op.drop_index(op.f("ix_health_measurements_measured_at"), table_name="health_measurements")
    op.drop_index(op.f("ix_health_measurements_patient_id"), table_name="health_measurements")
    op.drop_index(op.f("ix_health_measurements_owner_id"), table_name="health_measurements")
    op.drop_table("health_measurements")

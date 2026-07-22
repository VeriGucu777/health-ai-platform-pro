"""create medical records table

Revision ID: e4a5b6c7d8e9
Revises: d3f4a5b6c7e8
Create Date: 2026-07-21 18:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e4a5b6c7d8e9"
down_revision: Union[str, None] = "d3f4a5b6c7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medical_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("record_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("treatment", sa.Text(), nullable=True),
        sa.Column("medications", sa.Text(), nullable=True),
        sa.Column("doctor_name", sa.String(length=100), nullable=True),
        sa.Column("hospital_name", sa.String(length=200), nullable=True),
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
        op.f("ix_medical_records_owner_id"),
        "medical_records",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_medical_records_patient_id"),
        "medical_records",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_medical_records_record_type"),
        "medical_records",
        ["record_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_medical_records_record_type"), table_name="medical_records")
    op.drop_index(op.f("ix_medical_records_patient_id"), table_name="medical_records")
    op.drop_index(op.f("ix_medical_records_owner_id"), table_name="medical_records")
    op.drop_table("medical_records")

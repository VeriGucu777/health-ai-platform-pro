"""create clinical_retrieval_vectors with pgvector

Revision ID: l1m2n3o4p5q6
Revises: k0a1b2c3d4e5
Create Date: 2026-09-21 12:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "l1m2n3o4p5q6"
down_revision: Union[str, None] = "k0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 64


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "clinical_retrieval_vectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_id", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canonical_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id", name="uq_clinical_retrieval_vectors_evidence_id"),
    )
    op.create_index(
        "ix_clinical_retrieval_vectors_patient_id",
        "clinical_retrieval_vectors",
        ["patient_id"],
    )
    op.create_index(
        "ix_clinical_retrieval_vectors_org_patient",
        "clinical_retrieval_vectors",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_clinical_retrieval_vectors_source_type",
        "clinical_retrieval_vectors",
        ["source_type"],
    )
    # Pilot: patient_id scope narrows rows; add ANN index when dataset grows.


def downgrade() -> None:
    op.drop_index("ix_clinical_retrieval_vectors_source_type", table_name="clinical_retrieval_vectors")
    op.drop_index("ix_clinical_retrieval_vectors_org_patient", table_name="clinical_retrieval_vectors")
    op.drop_index("ix_clinical_retrieval_vectors_patient_id", table_name="clinical_retrieval_vectors")
    op.drop_table("clinical_retrieval_vectors")

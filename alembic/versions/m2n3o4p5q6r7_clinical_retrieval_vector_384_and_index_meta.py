"""clinical retrieval vectors: 384-dim pgvector and embedding metadata

Revision ID: m2n3o4p5q6r7
Revises: l1m2n3o4p5q6
Create Date: 2026-09-21 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "m2n3o4p5q6r7"
down_revision: Union[str, None] = "l1m2n3o4p5q6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRODUCTION_EMBEDDING_DIM = 384


def upgrade() -> None:
    # Pilot table only; safe to truncate before dimension change (64-d fake → 384-d local).
    op.execute("TRUNCATE TABLE clinical_retrieval_vectors")
    op.drop_column("clinical_retrieval_vectors", "embedding")
    op.add_column(
        "clinical_retrieval_vectors",
        sa.Column("embedding_version", sa.String(length=32), nullable=False, server_default="1"),
    )
    op.add_column(
        "clinical_retrieval_vectors",
        sa.Column("embedding_dimension", sa.Integer(), nullable=False, server_default="384"),
    )
    op.add_column(
        "clinical_retrieval_vectors",
        sa.Column("embedding", Vector(PRODUCTION_EMBEDDING_DIM), nullable=False),
    )
    op.alter_column("clinical_retrieval_vectors", "embedding_model", type_=sa.String(length=128))
    op.alter_column("clinical_retrieval_vectors", "embedding_version", server_default=None)
    op.alter_column("clinical_retrieval_vectors", "embedding_dimension", server_default=None)


def downgrade() -> None:
    op.execute("TRUNCATE TABLE clinical_retrieval_vectors")
    op.drop_column("clinical_retrieval_vectors", "embedding")
    op.drop_column("clinical_retrieval_vectors", "embedding_dimension")
    op.drop_column("clinical_retrieval_vectors", "embedding_version")
    op.add_column(
        "clinical_retrieval_vectors",
        sa.Column("embedding", Vector(64), nullable=False),
    )
    op.alter_column("clinical_retrieval_vectors", "embedding_model", type_=sa.String(length=64))

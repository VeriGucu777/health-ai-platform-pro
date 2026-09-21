"""add embedding_pooling_profile to clinical_retrieval_vectors

Revision ID: n3o4p5q6r7s8
Revises: m2n3o4p5q6r7
Create Date: 2026-09-21 15:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n3o4p5q6r7s8"
down_revision: Union[str, None] = "m2n3o4p5q6r7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_POOLING = "mean_l2_normalized_v1"


def upgrade() -> None:
    op.add_column(
        "clinical_retrieval_vectors",
        sa.Column(
            "embedding_pooling_profile",
            sa.String(length=64),
            nullable=False,
            server_default=DEFAULT_POOLING,
        ),
    )
    op.alter_column("clinical_retrieval_vectors", "embedding_pooling_profile", server_default=None)


def downgrade() -> None:
    op.drop_column("clinical_retrieval_vectors", "embedding_pooling_profile")

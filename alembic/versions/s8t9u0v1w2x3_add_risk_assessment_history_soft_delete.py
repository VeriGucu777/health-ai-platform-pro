"""add is_active and deleted_at to risk_assessment_history

Revision ID: s8t9u0v1w2x3
Revises: r7s8t9u0v1w2
Create Date: 2026-10-04 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s8t9u0v1w2x3"
down_revision: Union[str, None] = "r7s8t9u0v1w2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "risk_assessment_history",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "risk_assessment_history",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("risk_assessment_history", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("risk_assessment_history", "deleted_at")
    op.drop_column("risk_assessment_history", "is_active")

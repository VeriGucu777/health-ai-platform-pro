"""add is_active and deleted_at to clinical child tables

Revision ID: r7s8t9u0v1w2
Revises: q6r7s8t9u0v1
Create Date: 2026-10-01 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r7s8t9u0v1w2"
down_revision: Union[str, None] = "q6r7s8t9u0v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("health_measurements", "medical_records"):
        op.add_column(
            table,
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )
        op.add_column(
            table,
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.alter_column(table, "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("medical_records", "deleted_at")
    op.drop_column("medical_records", "is_active")
    op.drop_column("health_measurements", "deleted_at")
    op.drop_column("health_measurements", "is_active")

"""add users token_version

Revision ID: g6c7d8e9f0a1
Revises: f5b6c7d8e9f0
Create Date: 2026-09-19 10:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g6c7d8e9f0a1"
down_revision: Union[str, None] = "f5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")

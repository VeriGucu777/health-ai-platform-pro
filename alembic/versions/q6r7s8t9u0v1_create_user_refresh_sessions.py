"""create user_refresh_sessions for multi-device refresh rotation

Revision ID: q6r7s8t9u0v1
Revises: o4p5q6r7s8t0
Create Date: 2026-09-28 19:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "q6r7s8t9u0v1"
down_revision: Union[str, None] = "o4p5q6r7s8t0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_refresh_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_id_hash", sa.String(length=64), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_token_id_hash", name="uq_user_refresh_sessions_hash"),
    )
    op.create_index(
        "ix_user_refresh_sessions_user_id",
        "user_refresh_sessions",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_refresh_sessions_user_id", table_name="user_refresh_sessions")
    op.drop_table("user_refresh_sessions")

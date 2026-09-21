"""create audit_logs table

Revision ID: h7d8e9f0a1b2
Revises: g6c7d8e9f0a1
Create Date: 2026-09-19 11:25:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "h7d8e9f0a1b2"
down_revision: Union[str, None] = "g6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("http_status", sa.SmallInteger(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("route_template", sa.String(length=512), nullable=True),
        sa.Column("client_ip_truncated", sa.String(length=64), nullable=True),
        sa.Column("owner_scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_occurred_at_desc",
        "audit_logs",
        [sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_audit_logs_actor_id_occurred_at_desc",
        "audit_logs",
        ["actor_id", sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_audit_logs_resource_type_resource_id_occurred_at_desc",
        "audit_logs",
        ["resource_type", "resource_id", sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_audit_logs_owner_scope_id_occurred_at_desc",
        "audit_logs",
        ["owner_scope_id", sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_audit_logs_organization_id_occurred_at_desc",
        "audit_logs",
        ["organization_id", sa.text("occurred_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_organization_id_occurred_at_desc", table_name="audit_logs")
    op.drop_index("ix_audit_logs_owner_scope_id_occurred_at_desc", table_name="audit_logs")
    op.drop_index(
        "ix_audit_logs_resource_type_resource_id_occurred_at_desc",
        table_name="audit_logs",
    )
    op.drop_index("ix_audit_logs_actor_id_occurred_at_desc", table_name="audit_logs")
    op.drop_index("ix_audit_logs_occurred_at_desc", table_name="audit_logs")
    op.drop_table("audit_logs")

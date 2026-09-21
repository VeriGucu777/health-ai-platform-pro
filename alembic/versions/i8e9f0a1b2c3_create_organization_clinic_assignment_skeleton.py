"""create organization clinic assignment skeleton tables

Revision ID: i8e9f0a1b2c3
Revises: h7d8e9f0a1b2
Create Date: 2026-09-19 10:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "i8e9f0a1b2c3"
down_revision: Union[str, None] = "h7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index(
        "ix_organizations_is_active",
        "organizations",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membership_role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_memberships_org_user",
        ),
    )
    op.create_index(
        "ix_organization_memberships_org_status",
        "organization_memberships",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_organization_memberships_user_status",
        "organization_memberships",
        ["user_id", "status"],
        unique=False,
    )

    op.add_column(
        "patients",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_patients_organization_id_organizations",
        "patients",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_patients_organization_id",
        "patients",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_patients_organization_id_is_active",
        "patients",
        ["organization_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "patient_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignee_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_patient_assignments_assignee_status",
        "patient_assignments",
        ["assignee_user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_patient_assignments_patient_status",
        "patient_assignments",
        ["patient_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_patient_assignments_org_patient",
        "patient_assignments",
        ["organization_id", "patient_id"],
        unique=False,
    )
    op.create_index(
        "uq_patient_assignments_active_patient_assignee",
        "patient_assignments",
        ["patient_id", "assignee_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "uq_patient_assignments_active_primary_per_org_patient",
        "patient_assignments",
        ["patient_id", "organization_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND is_primary = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_patient_assignments_active_primary_per_org_patient",
        table_name="patient_assignments",
    )
    op.drop_index(
        "uq_patient_assignments_active_patient_assignee",
        table_name="patient_assignments",
    )
    op.drop_index("ix_patient_assignments_org_patient", table_name="patient_assignments")
    op.drop_index("ix_patient_assignments_patient_status", table_name="patient_assignments")
    op.drop_index("ix_patient_assignments_assignee_status", table_name="patient_assignments")
    op.drop_table("patient_assignments")

    op.drop_index("ix_patients_organization_id_is_active", table_name="patients")
    op.drop_index("ix_patients_organization_id", table_name="patients")
    op.drop_constraint("fk_patients_organization_id_organizations", "patients", type_="foreignkey")
    op.drop_column("patients", "organization_id")

    op.drop_index("ix_organization_memberships_user_status", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_org_status", table_name="organization_memberships")
    op.drop_table("organization_memberships")

    op.drop_index("ix_organizations_is_active", table_name="organizations")
    op.drop_table("organizations")

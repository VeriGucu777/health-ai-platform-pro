"""Organization membership ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole
from app.infrastructure.database.base import Base, UUIDPrimaryKeyMixin


class OrganizationMembershipModel(Base, UUIDPrimaryKeyMixin):
    """SQLAlchemy model for the organization_memberships table."""

    __tablename__ = "organization_memberships"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    membership_role: Mapped[OrganizationMembershipRole] = mapped_column(
        String(32),
        nullable=False,
    )
    status: Mapped[MembershipStatus] = mapped_column(
        String(16),
        nullable=False,
        default=MembershipStatus.ACTIVE,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

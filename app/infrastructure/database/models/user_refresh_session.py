"""User refresh session ORM model."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRefreshSessionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One refresh token rotation chain (typically one per device login)."""

    __tablename__ = "user_refresh_sessions"
    __table_args__ = (
        UniqueConstraint("refresh_token_id_hash", name="uq_user_refresh_sessions_hash"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_token_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)

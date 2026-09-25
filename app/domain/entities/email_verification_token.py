"""Email verification token domain entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities.base import BaseEntity


@dataclass(kw_only=True)
class EmailVerificationToken(BaseEntity):
    """One-time email verification token (hash stored, never raw)."""

    user_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None
    superseded_at: datetime | None = None

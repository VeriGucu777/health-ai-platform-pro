"""Refresh token session row (one active refresh chain per device/login)."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.base import BaseEntity


@dataclass(kw_only=True)
class UserRefreshSession(BaseEntity):
    """Server-side refresh rotation state; stores HMAC digest of jti only."""

    user_id: UUID
    refresh_token_id_hash: str

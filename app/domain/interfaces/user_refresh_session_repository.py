"""Refresh session persistence port."""

from abc import abstractmethod
from uuid import UUID

from app.domain.entities.user_refresh_session import UserRefreshSession
from app.domain.interfaces.repository import Repository


class UserRefreshSessionRepository(Repository[UserRefreshSession]):
    """Store per-login refresh rotation digests (multi-device safe)."""

    @abstractmethod
    async def get_by_hash(self, refresh_token_id_hash: str) -> UserRefreshSession | None:
        """Find session by current refresh digest."""

    @abstractmethod
    async def create_session(
        self,
        user_id: UUID,
        refresh_token_id_hash: str,
    ) -> UserRefreshSession:
        """Create a new refresh session (login or new device)."""

    @abstractmethod
    async def rotate_hash(self, session_id: UUID, refresh_token_id_hash: str) -> None:
        """Replace digest after successful refresh (invalidates previous refresh JWT)."""

    @abstractmethod
    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Remove all refresh sessions (logout / password change / token_version bump)."""

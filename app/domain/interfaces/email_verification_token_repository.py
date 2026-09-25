"""Repository port for email verification tokens."""

from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from app.domain.entities.email_verification_token import EmailVerificationToken
from app.domain.interfaces.repository import Repository


class EmailVerificationTokenRepository(Repository[EmailVerificationToken]):
    """Persistence for hashed verification tokens."""

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> EmailVerificationToken | None: ...

    @abstractmethod
    async def supersede_unused_for_user(self, user_id: UUID) -> int: ...

    @abstractmethod
    async def get_latest_for_user(self, user_id: UUID) -> EmailVerificationToken | None: ...

"""User repository port."""

from abc import abstractmethod
from uuid import UUID

from app.domain.entities.user import User
from app.domain.interfaces.repository import Repository


class UserRepository(Repository[User]):
    """Contract for user persistence operations."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Retrieve a user by normalized email address."""

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """Return True if the email is already registered."""

    @abstractmethod
    async def increment_token_version(self, user_id: UUID) -> User:
        """Increment token_version to invalidate outstanding JWTs."""

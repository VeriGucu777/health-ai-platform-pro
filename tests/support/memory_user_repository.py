"""In-memory user repository for API tests without a live database."""

from uuid import UUID

from app.domain.entities.user import User
from app.domain.interfaces.user_repository import UserRepository
from app.infrastructure.repositories.user_repository import normalize_email


class InMemoryUserRepository(UserRepository):
    """Thread-unsafe in-memory store — one instance per test via fixtures."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}
        self._emails: dict[str, UUID] = {}

    async def get_by_id(self, entity_id: UUID) -> User | None:
        return self._users.get(entity_id)

    async def get_by_email(self, email: str) -> User | None:
        user_id = self._emails.get(normalize_email(email))
        return self._users.get(user_id) if user_id else None

    async def email_exists(self, email: str) -> bool:
        return normalize_email(email) in self._emails

    async def create(self, entity: User) -> User:
        normalized = normalize_email(entity.email)
        if normalized in self._emails:
            msg = "Email already exists"
            raise ValueError(msg)
        self._users[entity.id] = entity
        self._emails[normalized] = entity.id
        return entity

    async def update(self, entity: User) -> User:
        if entity.id not in self._users:
            msg = "User not found"
            raise ValueError(msg)
        self._users[entity.id] = entity
        self._emails[normalize_email(entity.email)] = entity.id
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        user = self._users.pop(entity_id, None)
        if user is None:
            return False
        self._emails.pop(normalize_email(user.email), None)
        return True

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[User]:
        users = list(self._users.values())
        return users[offset : offset + limit]

    async def increment_token_version(self, user_id: UUID) -> User:
        user = self._users.get(user_id)
        if user is None:
            msg = "User not found"
            raise ValueError(msg)
        user.token_version += 1
        user.touch()
        return user

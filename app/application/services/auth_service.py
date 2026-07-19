"""Authentication application service."""

from uuid import UUID

from jose import JWTError

from app.application.dtos.user import TokenPairDTO, UserDTO
from app.application.services.base import BaseService
from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.entities.user import User, UserRole
from app.domain.interfaces.user_repository import UserRepository
from app.infrastructure.repositories.user_repository import normalize_email

_SELF_REGISTER_ROLES = {UserRole.PATIENT, UserRole.DOCTOR}


class AuthService(BaseService):
    """Handles registration, authentication, and token lifecycle."""

    def __init__(self, user_repository: UserRepository, settings: Settings) -> None:
        self._users = user_repository
        self._settings = settings

    async def register(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: UserRole = UserRole.PATIENT,
    ) -> UserDTO:
        normalized_email = normalize_email(email)

        if role not in _SELF_REGISTER_ROLES:
            raise ForbiddenError(
                "Self-registration is only allowed for patient and doctor roles",
            )

        if await self._users.email_exists(normalized_email):
            raise ConflictError("Email address is already registered")

        user = User(
            email=normalized_email,
            hashed_password=hash_password(password),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            role=role,
        )
        created = await self._users.create(user)
        return UserDTO.from_entity(created)

    async def login(self, *, email: str, password: str) -> TokenPairDTO:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise ForbiddenError("Account is deactivated")

        return self._build_token_pair(user)

    async def refresh_tokens(self, refresh_token: str) -> TokenPairDTO:
        user = await self._validate_token_user(refresh_token, expected_type="refresh")
        return self._build_token_pair(user)

    async def logout(self, refresh_token: str) -> None:
        """Validate refresh token — client must discard tokens after logout."""
        await self._validate_token_user(refresh_token, expected_type="refresh")

    async def get_current_user(self, user_id: UUID) -> UserDTO:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found")

        if not user.is_active:
            raise ForbiddenError("Account is deactivated")

        return UserDTO.from_entity(user)

    def _build_token_pair(self, user: User) -> TokenPairDTO:
        extra_claims = {"role": user.role.value}
        return TokenPairDTO(
            access_token=create_access_token(
                user.id,
                settings=self._settings,
                extra_claims=extra_claims,
            ),
            refresh_token=create_refresh_token(user.id, settings=self._settings),
        )

    async def _validate_token_user(
        self,
        token: str,
        *,
        expected_type: str,
    ) -> User:
        try:
            payload = decode_token(token, self._settings)
        except JWTError as exc:
            raise UnauthorizedError("Invalid or expired token") from exc

        token_type = payload.get("type")
        if token_type != expected_type:
            raise UnauthorizedError(f"Invalid token type: expected {expected_type}")

        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise UnauthorizedError("Invalid token payload")

        try:
            user_id = UUID(user_id_str)
        except ValueError as exc:
            raise UnauthorizedError("Invalid token subject") from exc

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found")

        if not user.is_active:
            raise ForbiddenError("Account is deactivated")

        return user

"""User-related application DTOs."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.domain.entities.user import User, UserRole


class UserDTO(BaseSchema):
    """User data returned from application services — never includes password hash."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    email_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserDTO":
        return cls(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            email_verified_at=user.email_verified_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class TokenPairDTO(BaseSchema):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"

"""Authentication endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_auth_service, require_roles
from app.api.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.application.dtos.user import UserDTO
from app.application.services.auth_service import AuthService
from app.domain.entities.user import UserRole

router = APIRouter()


def _user_response(user: UserDTO) -> UserResponse:
    return UserResponse.model_validate(user.model_dump())


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="User registration",
)
async def register(
    body: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Register a new user account."""
    user = await auth_service.register(
        email=body.email,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
        role=body.role,
    )
    return _user_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
)
async def login(
    body: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate user and return JWT tokens."""
    tokens = await auth_service.login(email=body.email, password=body.password)
    return TokenResponse.model_validate(tokens.model_dump())


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Exchange a refresh token for a new token pair."""
    tokens = await auth_service.refresh_tokens(body.refresh_token)
    return TokenResponse.model_validate(tokens.model_dump())


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="User logout",
)
async def logout(
    body: LogoutRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    """Validate refresh token and confirm logout (client must discard tokens)."""
    await auth_service.logout(body.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user profile",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Return the authenticated user's profile."""
    return _user_response(current_user)


@router.get(
    "/admin/ping",
    response_model=MessageResponse,
    summary="System admin health check",
    include_in_schema=True,
)
async def admin_ping(
    _admin: Annotated[UserDTO, Depends(require_roles(UserRole.SYSTEM_ADMIN))],
) -> MessageResponse:
    """Protected route requiring system_admin role."""
    return MessageResponse(message="Admin access granted")

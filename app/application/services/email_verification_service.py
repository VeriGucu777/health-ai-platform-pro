"""Email verification token lifecycle and outbound notifications."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from app.application.services.base import BaseService
from app.application.services.email_verification_token_crypto import (
    generate_raw_verification_token,
    hash_verification_token,
)
from app.core.config import Settings
from app.core.exceptions import AppException, RateLimitExceededError
from app.core.logging import get_logger
from app.domain.entities.email_verification_token import EmailVerificationToken
from app.domain.entities.user import User
from app.domain.interfaces.email_sender import EmailSender
from app.domain.interfaces.email_verification_token_repository import EmailVerificationTokenRepository
from app.domain.interfaces.user_repository import UserRepository
from app.infrastructure.repositories.user_repository import normalize_email

_logger = get_logger(__name__)

GENERIC_RESEND_MESSAGE = (
    "If an account exists for this email, a verification message has been sent."
)
INVALID_TOKEN_MESSAGE = "Invalid or expired verification token"


class EmailVerificationService(BaseService):
    """Issue, verify, and resend email verification tokens."""

    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: EmailVerificationTokenRepository,
        email_sender: EmailSender,
        settings: Settings,
    ) -> None:
        self._users = user_repository
        self._tokens = token_repository
        self._email_sender = email_sender
        self._settings = settings

    async def start_verification_for_user(self, user: User, *, locale: str = "en") -> None:
        """Create a verification token and queue email delivery (user already persisted)."""
        if user.is_verified:
            return
        raw_token = await self._issue_token(user.id)
        verify_url = self._build_verify_url(raw_token)
        try:
            await self._email_sender.send_verification_email(
                to_email=user.email,
                verify_url=verify_url,
                locale=locale,
            )
        except Exception:
            _logger.exception(
                "Verification email delivery failed user_id=%s",
                user.id,
            )

    async def verify_email(self, raw_token: str) -> None:
        """Mark the user verified when the token is valid."""
        token_hash = self._hash(raw_token)
        record = await self._tokens.get_by_token_hash(token_hash)
        if record is None or not self._token_is_valid(record):
            raise AppException(INVALID_TOKEN_MESSAGE, status_code=400)

        user = await self._users.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise AppException(INVALID_TOKEN_MESSAGE, status_code=400)

        if user.is_verified:
            record.used_at = record.used_at or datetime.now(UTC)
            await self._tokens.update(record)
            return

        now = datetime.now(UTC)
        record.used_at = now
        await self._tokens.update(record)

        user.is_verified = True
        user.email_verified_at = now
        user.touch()
        await self._users.update(user)

    async def resend_verification(self, email: str, *, locale: str = "en") -> str:
        """Resend verification email; response is always generic."""
        normalized = normalize_email(email)
        user = await self._users.get_by_email(normalized)
        if user is None or not user.is_active or user.is_verified:
            return GENERIC_RESEND_MESSAGE

        await self._enforce_resend_cooldown(user.id)
        raw_token = await self._issue_token(user.id)
        verify_url = self._build_verify_url(raw_token)
        try:
            await self._email_sender.send_verification_email(
                to_email=user.email,
                verify_url=verify_url,
                locale=locale,
            )
        except Exception:
            _logger.exception(
                "Verification resend delivery failed user_id=%s",
                user.id,
            )
        return GENERIC_RESEND_MESSAGE

    async def _issue_token(self, user_id) -> str:
        await self._tokens.supersede_unused_for_user(user_id)
        raw = generate_raw_verification_token()
        token_hash = self._hash(raw)
        expires_at = datetime.now(UTC) + timedelta(
            hours=self._settings.email_verification_token_ttl_hours,
        )
        await self._tokens.create(
            EmailVerificationToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            ),
        )
        return raw

    def _hash(self, raw_token: str) -> str:
        return hash_verification_token(
            raw_token,
            pepper=self._settings.email_verification_pepper,
        )

    def _build_verify_url(self, raw_token: str) -> str:
        base = self._settings.frontend_public_url.rstrip("/")
        return f"{base}/verify-email?token={quote(raw_token, safe='')}"

    def _token_is_valid(self, record: EmailVerificationToken) -> bool:
        now = datetime.now(UTC)
        if record.used_at is not None:
            return False
        if record.superseded_at is not None:
            return False
        return record.expires_at > now

    async def _enforce_resend_cooldown(self, user_id) -> None:
        latest = await self._tokens.get_latest_for_user(user_id)
        if latest is None:
            return
        cooldown = timedelta(seconds=self._settings.email_verification_resend_cooldown_seconds)
        if datetime.now(UTC) - latest.created_at < cooldown:
            raise RateLimitExceededError("Verification resend is temporarily unavailable")

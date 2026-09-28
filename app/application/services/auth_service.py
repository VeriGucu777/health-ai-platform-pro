"""Authentication application service."""

from uuid import UUID

from jose import JWTError

from app.application.dtos.auth_audit import AuthAuditContext
from app.application.dtos.user import TokenPairDTO, UserDTO
from app.application.services.auth_audit_recorder import record_auth_audit_event
from app.application.services.audit_service import AuditService
from app.application.services.base import BaseService
from app.application.services.email_verification_service import EmailVerificationService
from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.refresh_token_rotation import hash_refresh_jti, new_refresh_jti
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.token_validation import validate_token_claims, validate_token_version
from app.domain.audit.taxonomy import AuditAction, AuditOutcome
from app.domain.entities.user import User, UserRole
from app.domain.interfaces.user_refresh_session_repository import UserRefreshSessionRepository
from app.domain.interfaces.user_repository import UserRepository
from app.infrastructure.repositories.user_repository import normalize_email

_SELF_REGISTER_ROLES = {UserRole.PATIENT, UserRole.DOCTOR}


class AuthService(BaseService):
    """Handles registration, authentication, and token lifecycle."""

    def __init__(
        self,
        user_repository: UserRepository,
        settings: Settings,
        audit_service: AuditService | None = None,
        email_verification_service: EmailVerificationService | None = None,
        refresh_session_repository: UserRefreshSessionRepository | None = None,
    ) -> None:
        self._users = user_repository
        self._settings = settings
        self._audit = audit_service
        self._email_verification = email_verification_service
        self._refresh_sessions = refresh_session_repository

    async def register(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: UserRole = UserRole.PATIENT,
        locale: str = "en",
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
        if self._email_verification is not None:
            await self._email_verification.start_verification_for_user(
                created,
                locale=locale,
            )
        return UserDTO.from_entity(created)

    async def login(
        self,
        *,
        email: str,
        password: str,
        audit_context: AuthAuditContext | None = None,
    ) -> TokenPairDTO:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            await record_auth_audit_event(
                self._audit,
                action=AuditAction.LOGIN_FAILURE,
                outcome=AuditOutcome.FAILURE,
                http_status=401,
                audit_context=audit_context,
                metadata={"reason_code": "invalid_credentials"},
            )
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            await record_auth_audit_event(
                self._audit,
                action=AuditAction.LOGIN_FAILURE,
                outcome=AuditOutcome.FAILURE,
                http_status=403,
                audit_context=audit_context,
                metadata={"reason_code": "inactive_account"},
            )
            raise ForbiddenError("Account is deactivated")

        await self._ensure_email_verified_for_auth(
            user,
            audit_context=audit_context,
            audit_action=AuditAction.LOGIN_FAILURE,
        )

        tokens = await self._issue_token_pair(user)
        await record_auth_audit_event(
            self._audit,
            action=AuditAction.LOGIN_SUCCESS,
            outcome=AuditOutcome.SUCCESS,
            http_status=200,
            audit_context=audit_context,
            actor=user,
        )
        return tokens

    async def refresh_tokens(
        self,
        refresh_token: str,
        *,
        audit_context: AuthAuditContext | None = None,
    ) -> TokenPairDTO:
        try:
            payload = decode_token(refresh_token, self._settings)
            user_id_str = validate_token_claims(payload, expected_type="refresh")
            user_id = UUID(user_id_str)
        except (JWTError, ValueError) as exc:
            raise UnauthorizedError("Invalid or expired token") from exc

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("Invalid or expired token")

        jti = payload.get("jti")
        jti_str = str(jti) if jti else None
        refresh_session = await self._resolve_refresh_session(user, jti_str)
        if refresh_session is None:
            await record_auth_audit_event(
                self._audit,
                action=AuditAction.TOKEN_REFRESH,
                outcome=AuditOutcome.FAILURE,
                http_status=401,
                audit_context=audit_context,
                actor=user,
                metadata={"reason_code": "refresh_token_reuse"},
            )
            raise UnauthorizedError("Invalid or expired token")

        try:
            validate_token_version(payload, user.token_version)
        except JWTError as exc:
            raise UnauthorizedError("Invalid or expired token") from exc

        if not user.is_active:
            raise ForbiddenError("Account is deactivated")

        await self._ensure_email_verified_for_auth(user)

        session_id = getattr(refresh_session, "id", None)
        tokens = await self._issue_token_pair(user, refresh_session_id=session_id)
        await record_auth_audit_event(
            self._audit,
            action=AuditAction.TOKEN_REFRESH,
            outcome=AuditOutcome.SUCCESS,
            http_status=200,
            audit_context=audit_context,
            actor=user,
        )
        return tokens

    async def logout(
        self,
        refresh_token: str,
        *,
        audit_context: AuthAuditContext | None = None,
    ) -> None:
        """Invalidate all outstanding tokens for the user after validating refresh."""
        user = await self._validate_token_user(refresh_token, expected_type="refresh")
        await self._revoke_all_refresh_sessions(user.id)
        await self._users.increment_token_version(user.id)
        await record_auth_audit_event(
            self._audit,
            action=AuditAction.LOGOUT,
            outcome=AuditOutcome.SUCCESS,
            http_status=200,
            audit_context=audit_context,
            actor=user,
        )

    async def change_password(
        self,
        user_id: UUID,
        *,
        current_password: str,
        new_password: str,
        audit_context: AuthAuditContext | None = None,
    ) -> None:
        """Change password and invalidate existing sessions."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found")

        if not verify_password(current_password, user.hashed_password):
            raise UnauthorizedError("Invalid current password")

        if not user.is_active:
            raise ForbiddenError("Account is deactivated")

        user.hashed_password = hash_password(new_password)
        user.token_version += 1
        await self._revoke_all_refresh_sessions(user.id)
        await self._users.update(user)
        await record_auth_audit_event(
            self._audit,
            action=AuditAction.PASSWORD_CHANGE,
            outcome=AuditOutcome.SUCCESS,
            http_status=200,
            audit_context=audit_context,
            actor=user,
        )

    async def validate_access_token(self, access_token: str) -> UUID:
        """Decode an access token and verify it has not been revoked."""
        return await self._validate_token_subject(
            access_token,
            expected_type="access",
        )

    async def resolve_access_token_user_id(self, access_token: str) -> UUID:
        """Validate an access token including token_version and return the user id."""
        return await self.validate_access_token(access_token)

    async def get_current_user(self, user_id: UUID) -> UserDTO:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found")

        if not user.is_active:
            raise ForbiddenError("Account is deactivated")

        await self._ensure_email_verified_for_auth(user)

        return UserDTO.from_entity(user)

    async def _ensure_email_verified_for_auth(
        self,
        user: User,
        *,
        audit_context: AuthAuditContext | None = None,
        audit_action: AuditAction = AuditAction.LOGIN_FAILURE,
    ) -> None:
        if not self._settings.email_verification_enforced:
            return
        if user.is_verified:
            return
        await record_auth_audit_event(
            self._audit,
            action=audit_action,
            outcome=AuditOutcome.FAILURE,
            http_status=403,
            audit_context=audit_context,
            metadata={"reason_code": "email_not_verified"},
        )
        raise ForbiddenError(
            "Email address is not verified",
            details={"reason_code": "email_not_verified"},
        )

    async def _issue_token_pair(
        self,
        user: User,
        *,
        refresh_session_id: UUID | None = None,
    ) -> TokenPairDTO:
        jti = new_refresh_jti()
        digest = hash_refresh_jti(jti=jti, settings=self._settings)
        refresh_sessions = self._require_refresh_sessions()
        if refresh_session_id is not None:
            await refresh_sessions.rotate_hash(refresh_session_id, digest)
        else:
            await refresh_sessions.create_session(user.id, digest)
        extra_claims = {"role": user.role.value}
        return TokenPairDTO(
            access_token=create_access_token(
                user.id,
                settings=self._settings,
                extra_claims=extra_claims,
                token_version=user.token_version,
            ),
            refresh_token=create_refresh_token(
                user.id,
                settings=self._settings,
                token_version=user.token_version,
                jti=jti,
            ),
        )

    async def _resolve_refresh_session(self, user: User, jti_str: str | None):
        if not jti_str:
            return None
        digest = hash_refresh_jti(jti=jti_str, settings=self._settings)
        session = await self._require_refresh_sessions().get_by_hash(digest)
        if session is None or session.user_id != user.id:
            return None
        return session

    async def _revoke_all_refresh_sessions(self, user_id: UUID) -> None:
        await self._require_refresh_sessions().revoke_all_for_user(user_id)

    def _require_refresh_sessions(self) -> UserRefreshSessionRepository:
        if self._refresh_sessions is None:
            msg = "Refresh session repository is not configured"
            raise RuntimeError(msg)
        return self._refresh_sessions

    async def _validate_token_subject(
        self,
        token: str,
        *,
        expected_type: str,
    ) -> UUID:
        try:
            payload = decode_token(token, self._settings)
            user_id_str = validate_token_claims(payload, expected_type=expected_type)
            user_id = UUID(user_id_str)
        except (JWTError, ValueError) as exc:
            raise UnauthorizedError("Invalid or expired token") from exc

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("Invalid or expired token")

        try:
            validate_token_version(payload, user.token_version)
        except JWTError as exc:
            raise UnauthorizedError("Invalid or expired token") from exc

        if not user.is_active:
            raise ForbiddenError("Account is deactivated")

        await self._ensure_email_verified_for_auth(user)

        return user_id

    async def _validate_token_user(
        self,
        token: str,
        *,
        expected_type: str,
    ) -> User:
        user_id = await self._validate_token_subject(token, expected_type=expected_type)
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("Invalid or expired token")
        return user

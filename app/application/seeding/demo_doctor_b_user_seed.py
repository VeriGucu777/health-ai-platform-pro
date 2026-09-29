"""Idempotent demo doctor B user ensure (ops seed only — password from env)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.security import hash_password, verify_password
from app.domain.entities.user import User, UserRole
from app.domain.interfaces.user_repository import UserRepository
from app.infrastructure.repositories.user_repository import normalize_email

DEFAULT_DEMO_DOCTOR_B_EMAIL = "doctor.demo2@example.com"
DEFAULT_DEMO_DOCTOR_B_DISPLAY_NAME = "Demo Doctor Two"


@dataclass(frozen=True)
class DemoDoctorBUserSeedConfig:
    email: str = DEFAULT_DEMO_DOCTOR_B_EMAIL
    password: str | None = None
    display_name: str = DEFAULT_DEMO_DOCTOR_B_DISPLAY_NAME


@dataclass(frozen=True)
class DemoDoctorBUserSeedResult:
    user_id: str
    email: str
    created_user: bool
    password_reset: bool
    activated_user: bool
    verified_user: bool


def split_demo_doctor_display_name(display_name: str) -> tuple[str, str]:
    """Split a display name into first and last name for user records."""
    parts = display_name.strip().split(None, 1)
    if not parts:
        return "Demo", "Doctor Two"
    if len(parts) == 1:
        return parts[0], "Doctor"
    return parts[0], parts[1]


async def ensure_demo_doctor_b_user(
    user_repository: UserRepository,
    *,
    config: DemoDoctorBUserSeedConfig,
    allow_password_reset: bool = True,
) -> DemoDoctorBUserSeedResult:
    """Create or repair demo doctor B (verified, active). Password required for create/reset."""
    normalized = normalize_email(config.email)
    first_name, last_name = split_demo_doctor_display_name(config.display_name)
    existing = await user_repository.get_by_email(normalized)

    if existing is None:
        if not config.password or not config.password.strip():
            msg = "DEMO_DOCTOR_B_PASSWORD is required to create demo doctor B"
            raise ValueError(msg)
        now = datetime.now(UTC)
        user = User(
            email=normalized,
            hashed_password=hash_password(config.password),
            first_name=first_name,
            last_name=last_name,
            role=UserRole.DOCTOR,
            is_active=True,
            is_verified=True,
            email_verified_at=now,
        )
        created = await user_repository.create(user)
        return DemoDoctorBUserSeedResult(
            user_id=str(created.id),
            email=created.email,
            created_user=True,
            password_reset=True,
            activated_user=True,
            verified_user=True,
        )

    if existing.role != UserRole.DOCTOR:
        msg = f"User {config.email!r} exists but role is {existing.role!r}; fix manually."
        raise ValueError(msg)

    password_reset = False
    if allow_password_reset and config.password and config.password.strip():
        password_reset = not verify_password(config.password, existing.hashed_password)
        if password_reset:
            existing.hashed_password = hash_password(config.password)
            existing.token_version += 1

    activated_user = not existing.is_active
    if activated_user:
        existing.is_active = True

    verified_user = not existing.is_verified
    if verified_user:
        existing.is_verified = True
        existing.email_verified_at = existing.email_verified_at or datetime.now(UTC)

    name_changed = (
        existing.first_name != first_name.strip()
        or existing.last_name != last_name.strip()
    )
    if name_changed:
        existing.first_name = first_name.strip()
        existing.last_name = last_name.strip()

    if password_reset or activated_user or verified_user or name_changed:
        await user_repository.update(existing)

    return DemoDoctorBUserSeedResult(
        user_id=str(existing.id),
        email=existing.email,
        created_user=False,
        password_reset=password_reset,
        activated_user=activated_user,
        verified_user=verified_user,
    )

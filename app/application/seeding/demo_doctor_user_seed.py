"""Idempotent demo doctor user ensure + password reset (ops seed only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.seeding.demo_organization_fixture_seed import DEMO_DOCTOR_EMAIL
from app.core.security import hash_password, verify_password
from app.domain.entities.user import User, UserRole
from app.domain.interfaces.user_repository import UserRepository
from app.infrastructure.repositories.user_repository import normalize_email

DEMO_DOCTOR_PASSWORD = "Demo12345!"
DEMO_DOCTOR_FIRST_NAME = "Demo"
DEMO_DOCTOR_LAST_NAME = "Doctor One"


@dataclass(frozen=True)
class DemoDoctorUserSeedConfig:
    email: str = DEMO_DOCTOR_EMAIL
    password: str = DEMO_DOCTOR_PASSWORD
    first_name: str = DEMO_DOCTOR_FIRST_NAME
    last_name: str = DEMO_DOCTOR_LAST_NAME


@dataclass(frozen=True)
class DemoDoctorUserSeedResult:
    user_id: str
    created_user: bool
    password_reset: bool
    activated_user: bool
    role: str


async def ensure_demo_doctor_user(
    user_repository: UserRepository,
    *,
    config: DemoDoctorUserSeedConfig | None = None,
) -> DemoDoctorUserSeedResult:
    """Create or reset the demo doctor account without touching org fixtures."""
    cfg = config or DemoDoctorUserSeedConfig()
    normalized = normalize_email(cfg.email)
    existing = await user_repository.get_by_email(normalized)

    if existing is None:
        now = datetime.now(UTC)
        user = User(
            email=normalized,
            hashed_password=hash_password(cfg.password),
            first_name=cfg.first_name.strip(),
            last_name=cfg.last_name.strip(),
            role=UserRole.DOCTOR,
            is_active=True,
            is_verified=True,
            email_verified_at=now,
        )
        created = await user_repository.create(user)
        return DemoDoctorUserSeedResult(
            user_id=str(created.id),
            created_user=True,
            password_reset=True,
            activated_user=True,
            role=created.role.value,
        )

    if existing.role != UserRole.DOCTOR:
        msg = f"User {cfg.email!r} exists but role is {existing.role!r}; fix manually."
        raise ValueError(msg)

    password_reset = not verify_password(cfg.password, existing.hashed_password)
    activated_user = not existing.is_active

    if password_reset:
        existing.hashed_password = hash_password(cfg.password)
        existing.token_version += 1

    if activated_user:
        existing.is_active = True

    verified_user = not existing.is_verified
    if verified_user:
        existing.is_verified = True
        existing.email_verified_at = existing.email_verified_at or datetime.now(UTC)

    if password_reset or activated_user or verified_user:
        await user_repository.update(existing)

    return DemoDoctorUserSeedResult(
        user_id=str(existing.id),
        created_user=False,
        password_reset=password_reset,
        activated_user=activated_user,
        role=existing.role.value,
    )

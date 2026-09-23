"""Unit tests for idempotent demo doctor user seed."""

import pytest

from app.application.seeding.demo_doctor_user_seed import (
    DemoDoctorUserSeedConfig,
    ensure_demo_doctor_user,
)
from app.core.security import verify_password
from app.domain.entities.user import User, UserRole
from app.infrastructure.repositories.user_repository import normalize_email
from tests.support.memory_user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_ensure_demo_doctor_creates_user_when_missing() -> None:
    repo = InMemoryUserRepository()
    result = await ensure_demo_doctor_user(
        repo,
        config=DemoDoctorUserSeedConfig(email="doctor.demo1@gmail.com", password="Demo12345!"),
    )
    assert result.created_user is True
    assert result.password_reset is True
    assert result.role == "doctor"
    user = await repo.get_by_email("doctor.demo1@gmail.com")
    assert user is not None
    assert user.is_active is True
    assert verify_password("Demo12345!", user.hashed_password)


@pytest.mark.asyncio
async def test_ensure_demo_doctor_resets_password_idempotently() -> None:
    repo = InMemoryUserRepository()
    config = DemoDoctorUserSeedConfig(email="doctor.demo1@gmail.com", password="Demo12345!")
    first = await ensure_demo_doctor_user(repo, config=config)
    second = await ensure_demo_doctor_user(repo, config=config)
    assert first.created_user is True
    assert second.created_user is False
    assert second.password_reset is False
    user = await repo.get_by_email("doctor.demo1@gmail.com")
    assert user is not None
    assert verify_password("Demo12345!", user.hashed_password)


@pytest.mark.asyncio
async def test_ensure_demo_doctor_rejects_non_doctor_role() -> None:
    repo = InMemoryUserRepository()
    email = normalize_email("doctor.demo1@gmail.com")
    await repo.create(
        User(
            email=email,
            hashed_password="x",
            first_name="A",
            last_name="B",
            role=UserRole.PATIENT,
        )
    )
    with pytest.raises(ValueError, match="role"):
        await ensure_demo_doctor_user(repo, config=DemoDoctorUserSeedConfig(email=email))


@pytest.mark.asyncio
async def test_ensure_demo_doctor_reactivates_inactive_account() -> None:
    repo = InMemoryUserRepository()
    config = DemoDoctorUserSeedConfig(email="doctor.demo1@gmail.com", password="Demo12345!")
    await ensure_demo_doctor_user(repo, config=config)
    user = await repo.get_by_email("doctor.demo1@gmail.com")
    assert user is not None
    user.is_active = False
    await repo.update(user)
    result = await ensure_demo_doctor_user(repo, config=config)
    assert result.activated_user is True
    refreshed = await repo.get_by_email("doctor.demo1@gmail.com")
    assert refreshed is not None
    assert refreshed.is_active is True

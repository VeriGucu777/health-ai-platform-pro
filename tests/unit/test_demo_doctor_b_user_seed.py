"""Unit tests for demo doctor B seed."""

import pytest

from app.application.seeding.demo_doctor_b_user_seed import (
    DemoDoctorBUserSeedConfig,
    ensure_demo_doctor_b_user,
    split_demo_doctor_display_name,
)
from app.core.security import hash_password, verify_password
from app.domain.entities.user import User, UserRole
from tests.support.memory_user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_ensure_demo_doctor_b_creates_verified_doctor() -> None:
    repo = InMemoryUserRepository()
    result = await ensure_demo_doctor_b_user(
        repo,
        config=DemoDoctorBUserSeedConfig(
            email="doctor-b-seed@example.com",
            password="UnitTestDoctorBPass1!",
            display_name="Demo Doctor Two",
        ),
    )
    user = await repo.get_by_email("doctor-b-seed@example.com")
    assert result.created_user is True
    assert user is not None
    assert user.is_verified is True
    assert user.email_verified_at is not None
    assert verify_password("UnitTestDoctorBPass1!", user.hashed_password)


@pytest.mark.asyncio
async def test_ensure_demo_doctor_b_idempotent_no_duplicate() -> None:
    repo = InMemoryUserRepository()
    config = DemoDoctorBUserSeedConfig(
        email="doctor-b-dup@example.com",
        password="UnitTestDoctorBPass1!",
    )
    first = await ensure_demo_doctor_b_user(repo, config=config)
    second = await ensure_demo_doctor_b_user(repo, config=config)
    assert first.created_user is True
    assert second.created_user is False
    assert len(await repo.list_all()) == 1


@pytest.mark.asyncio
async def test_ensure_demo_doctor_b_requires_password_for_create() -> None:
    repo = InMemoryUserRepository()
    with pytest.raises(ValueError, match="DEMO_DOCTOR_B_PASSWORD"):
        await ensure_demo_doctor_b_user(
            repo,
            config=DemoDoctorBUserSeedConfig(email="new-b@example.com", password=None),
        )


def test_split_display_name() -> None:
    assert split_demo_doctor_display_name("Demo Doctor Two") == ("Demo", "Doctor Two")

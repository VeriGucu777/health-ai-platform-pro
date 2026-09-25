"""Email verification acceptance tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

from app.application.seeding.demo_clinic_admin_seed import seed_demo_clinic_admin
from app.application.seeding.demo_doctor_user_seed import ensure_demo_doctor_user
from app.application.services.email_verification_service import GENERIC_RESEND_MESSAGE
from app.application.services.email_verification_token_crypto import hash_verification_token
from app.core.security import hash_password
from app.domain.entities.user import User, UserRole
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)
from tests.support.memory_organization_repository import InMemoryOrganizationRepository
from tests.support.memory_user_repository import InMemoryUserRepository
REGISTER = {
    "email": "verify-me@example.com",
    "password": "securepass123",
    "first_name": "Verify",
    "last_name": "Me",
    "role": "doctor",
}


def _token_from_sender(recording_email_sender) -> str:
    assert recording_email_sender.sent
    url = recording_email_sender.sent[-1].verify_url
    parsed = parse_qs(urlparse(url).query)
    return parsed["token"][0]


@pytest.fixture
def enforce_verification(app):
    app.state.settings = app.state.settings.model_copy(
        update={"email_verification_enforced": True},
    )
    yield app
    app.state.settings = app.state.settings.model_copy(
        update={"email_verification_enforced": False},
    )


@pytest.mark.asyncio
async def test_register_sets_unverified_and_queues_email(
    client: AsyncClient,
    recording_email_sender,
    email_verification_token_repository,
) -> None:
    response = await client.post("/api/v1/auth/register", json=REGISTER)
    assert response.status_code == 201
    body = response.json()
    assert body["is_verified"] is False
    assert body.get("email_verified_at") in (None, "")
    assert len(recording_email_sender.sent) == 1
    stored = email_verification_token_repository.all_tokens()
    assert len(stored) == 1
    assert stored[0].token_hash
    assert "token=" not in str(stored[0].token_hash)


@pytest.mark.asyncio
async def test_verify_success_and_login(
    client: AsyncClient,
    enforce_verification,
    recording_email_sender,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    token = _token_from_sender(recording_email_sender)
    verify = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verify.status_code == 200

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_login_before_verify_blocked_when_enforced(
    client: AsyncClient,
    enforce_verification,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert login.status_code == 403
    payload = login.json()
    assert payload["details"]["reason_code"] == "email_not_verified"


@pytest.mark.asyncio
async def test_invalid_token_generic_400(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/verify-email",
        json={"token": "x" * 32},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_expired_token_rejected(
    client: AsyncClient,
    recording_email_sender,
    email_verification_token_repository,
    test_settings,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    raw = _token_from_sender(recording_email_sender)
    row = email_verification_token_repository.all_tokens()[0]
    row.expires_at = datetime.now(UTC) - timedelta(minutes=5)
    expired = await client.post("/api/v1/auth/verify-email", json={"token": raw})
    assert expired.status_code == 400


@pytest.mark.asyncio
async def test_used_token_replay_rejected(
    client: AsyncClient,
    recording_email_sender,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    raw = _token_from_sender(recording_email_sender)
    first = await client.post("/api/v1/auth/verify-email", json={"token": raw})
    assert first.status_code == 200
    replay = await client.post("/api/v1/auth/verify-email", json={"token": raw})
    assert replay.status_code == 400


@pytest.mark.asyncio
async def test_resend_supersedes_old_token(
    client: AsyncClient,
    recording_email_sender,
    test_settings,
    app,
) -> None:
    app.state.settings = app.state.settings.model_copy(
        update={"email_verification_resend_cooldown_seconds": 0},
    )
    await client.post("/api/v1/auth/register", json=REGISTER)
    old_raw = _token_from_sender(recording_email_sender)
    resend = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": REGISTER["email"]},
    )
    assert resend.status_code == 200
    new_raw = _token_from_sender(recording_email_sender)
    assert new_raw != old_raw
    stale = await client.post("/api/v1/auth/verify-email", json={"token": old_raw})
    assert stale.status_code == 400
    fresh = await client.post("/api/v1/auth/verify-email", json={"token": new_raw})
    assert fresh.status_code == 200


@pytest.mark.asyncio
async def test_resend_unknown_email_generic(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "missing@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == GENERIC_RESEND_MESSAGE


@pytest.mark.asyncio
async def test_resend_verified_email_generic(
    client: AsyncClient,
    user_repository: InMemoryUserRepository,
    recording_email_sender,
) -> None:
    await user_repository.create(
        User(
            email="verified@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Ver",
            last_name="Ified",
            role=UserRole.DOCTOR,
            is_verified=True,
            email_verified_at=datetime.now(UTC),
        ),
    )
    before = len(recording_email_sender.sent)
    response = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "verified@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == GENERIC_RESEND_MESSAGE
    assert len(recording_email_sender.sent) == before


@pytest.mark.asyncio
async def test_resend_throttled(
    client: AsyncClient,
    app,
    recording_email_sender,
) -> None:
    app.state.settings = app.state.settings.model_copy(
        update={"email_verification_resend_cooldown_seconds": 3600},
    )
    await client.post("/api/v1/auth/register", json=REGISTER)
    second = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": REGISTER["email"]},
    )
    assert second.status_code == 429


@pytest.mark.asyncio
async def test_refresh_blocked_when_unverified(
    client: AsyncClient,
    user_repository: InMemoryUserRepository,
    enforce_verification,
    app,
) -> None:
    user = await user_repository.create(
        User(
            email="refresh@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Re",
            last_name="Fresh",
            role=UserRole.PATIENT,
            is_verified=False,
        ),
    )
    from app.application.services.auth_service import AuthService

    auth = AuthService(
        user_repository,
        app.state.settings,
        email_verification_service=None,
    )
    tokens = auth._build_token_pair(user)  # noqa: SLF001
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens.refresh_token},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_access_token_blocked_when_enforcement_turned_on(
    client: AsyncClient,
    app,
    recording_email_sender,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert login.status_code == 200
    access = login.json()["access_token"]
    app.state.settings = app.state.settings.model_copy(
        update={"email_verification_enforced": True},
    )
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert me.status_code == 403
    assert me.json()["details"]["reason_code"] == "email_not_verified"


@pytest.mark.asyncio
async def test_me_verified_user_success(
    client: AsyncClient,
    app,
    user_repository: InMemoryUserRepository,
) -> None:
    user = await user_repository.create(
        User(
            email="verified-me@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Ver",
            last_name="Ified",
            role=UserRole.DOCTOR,
            is_verified=True,
            email_verified_at=datetime.now(UTC),
        ),
    )
    from app.application.services.auth_service import AuthService

    auth = AuthService(user_repository, app.state.settings)
    tokens = auth._build_token_pair(user)  # noqa: SLF001
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
    )
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_me_unverified_blocked_with_reason_when_enforced(
    client: AsyncClient,
    app,
    enforce_verification,
    user_repository: InMemoryUserRepository,
) -> None:
    user = await user_repository.create(
        User(
            email="unverified-me@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Un",
            last_name="Verified",
            role=UserRole.DOCTOR,
            is_verified=False,
        ),
    )
    from app.application.services.auth_service import AuthService

    auth = AuthService(user_repository, app.state.settings)
    tokens = auth._build_token_pair(user)  # noqa: SLF001
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
    )
    assert me.status_code == 403
    assert me.json()["details"]["reason_code"] == "email_not_verified"


@pytest.mark.asyncio
async def test_me_unverified_allowed_when_enforcement_off(
    client: AsyncClient,
    app,
    user_repository: InMemoryUserRepository,
) -> None:
    user = await user_repository.create(
        User(
            email="legacy-me@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Leg",
            last_name="Acy",
            role=UserRole.DOCTOR,
            is_verified=False,
        ),
    )
    from app.application.services.auth_service import AuthService

    auth = AuthService(user_repository, app.state.settings)
    tokens = auth._build_token_pair(user)  # noqa: SLF001
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
    )
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_me_inactive_user_forbidden(
    client: AsyncClient,
    app,
    user_repository: InMemoryUserRepository,
) -> None:
    user = await user_repository.create(
        User(
            email="inactive-me@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="In",
            last_name="Active",
            role=UserRole.DOCTOR,
            is_active=False,
            is_verified=True,
        ),
    )
    from app.application.services.auth_service import AuthService

    auth = AuthService(user_repository, app.state.settings)
    tokens = auth._build_token_pair(user)  # noqa: SLF001
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
    )
    assert me.status_code == 403
    assert me.json()["message"] == "Account is deactivated"


@pytest.mark.asyncio
async def test_feature_flag_off_allows_unverified_login(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_inactive_user_login_still_blocked(client: AsyncClient, user_repository) -> None:
    await user_repository.create(
        User(
            email="inactive@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="In",
            last_name="Active",
            role=UserRole.PATIENT,
            is_active=False,
        ),
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "securepass123"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_demo_doctor_seed_is_verified() -> None:
    users = InMemoryUserRepository()
    await ensure_demo_doctor_user(users)
    doctor = await users.get_by_email("doctor.demo1@gmail.com")
    assert doctor is not None
    assert doctor.is_verified is True
    assert doctor.email_verified_at is not None


@pytest.mark.asyncio
async def test_demo_clinic_admin_seed_is_verified() -> None:
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    await seed_demo_clinic_admin(
        user_repository=users,
        organization_repository=orgs,
        membership_repository=memberships,
    )
    admin = await users.get_by_email("live-pa-admin-c45d9a48@example.com")
    assert admin is not None
    assert admin.is_verified is True


@pytest.mark.asyncio
async def test_raw_token_not_equal_to_hash(
    client: AsyncClient,
    recording_email_sender,
    email_verification_token_repository,
    test_settings,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    raw = _token_from_sender(recording_email_sender)
    row = email_verification_token_repository.all_tokens()[0]
    assert row.token_hash != raw
    assert row.token_hash == hash_verification_token(
        raw,
        pepper=test_settings.email_verification_pepper,
    )

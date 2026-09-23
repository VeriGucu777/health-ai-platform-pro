#!/usr/bin/env python3
"""Seed demo clinic admin user + organization for Render/E2E (run manually with DATABASE_URL)."""

from __future__ import annotations

import asyncio
import os
import sys

# Allow `python scripts/seed_demo_clinic_admin.py` from backend root.
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.application.seeding.demo_clinic_admin_seed import (  # noqa: E402
    DEMO_CLINIC_ADMIN_EMAIL,
    DEMO_CLINIC_ADMIN_FIRST_NAME,
    DEMO_CLINIC_ADMIN_LAST_NAME,
    DEMO_CLINIC_ADMIN_PASSWORD,
    DEMO_ORGANIZATION_NAME,
    DEMO_ORGANIZATION_SLUG,
    DemoClinicAdminSeedConfig,
    seed_demo_clinic_admin,
)
from app.core.config import Settings, get_settings  # noqa: E402
from app.infrastructure.database.session import (  # noqa: E402
    dispose_engine,
    get_session_factory,
    reset_database_engine,
)
from app.infrastructure.repositories.organization_membership_repository import (  # noqa: E402
    SQLAlchemyOrganizationMembershipRepository,
)
from app.infrastructure.repositories.organization_repository import (  # noqa: E402
    SQLAlchemyOrganizationRepository,
)
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository  # noqa: E402


def _seed_config_from_env() -> DemoClinicAdminSeedConfig:
    return DemoClinicAdminSeedConfig(
        email=os.getenv("DEMO_CLINIC_ADMIN_EMAIL", DEMO_CLINIC_ADMIN_EMAIL),
        password=os.getenv("DEMO_CLINIC_ADMIN_PASSWORD", DEMO_CLINIC_ADMIN_PASSWORD),
        first_name=os.getenv("DEMO_CLINIC_ADMIN_FIRST_NAME", DEMO_CLINIC_ADMIN_FIRST_NAME),
        last_name=os.getenv("DEMO_CLINIC_ADMIN_LAST_NAME", DEMO_CLINIC_ADMIN_LAST_NAME),
        organization_name=os.getenv("DEMO_ORGANIZATION_NAME", DEMO_ORGANIZATION_NAME),
        organization_slug=os.getenv("DEMO_ORGANIZATION_SLUG", DEMO_ORGANIZATION_SLUG),
    )


def _ensure_database_url(settings: Settings) -> None:
    if not str(settings.database_url).strip():
        print("DATABASE_URL is required.", file=sys.stderr)
        sys.exit(1)


async def _run() -> int:
    settings = get_settings()
    _ensure_database_url(settings)
    config = _seed_config_from_env()

    reset_database_engine()
    session_factory = get_session_factory(settings)
    try:
        async with session_factory() as session:
            result = await seed_demo_clinic_admin(
                user_repository=SQLAlchemyUserRepository(session),
                organization_repository=SQLAlchemyOrganizationRepository(session),
                membership_repository=SQLAlchemyOrganizationMembershipRepository(session),
                config=config,
            )
            await session.commit()
    finally:
        await dispose_engine()

    print(
        "Demo clinic admin seed finished "
        f"(user_id={result.user_id}, organization_id={result.organization_id}, "
        f"created_user={result.created_user}, "
        f"created_organization={result.created_organization}, "
        f"created_membership={result.created_membership})",
    )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Seed demo doctor membership, patient, and assignment for /management (DATABASE_URL required)."""

from __future__ import annotations

import asyncio
import os
import sys

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.application.seeding.demo_organization_fixture_seed import (  # noqa: E402
    DEMO_DOCTOR_EMAIL,
    DEMO_ORGANIZATION_SLUG,
    DEMO_PATIENT_FIRST_NAME,
    DEMO_PATIENT_GENDER,
    DEMO_PATIENT_LAST_NAME,
    DEMO_PATIENT_SEED_MARKER,
    DemoOrganizationFixtureSeedConfig,
    seed_demo_organization_fixtures,
)
from app.application.seeding.demo_clinic_admin_seed import DEMO_CLINIC_ADMIN_EMAIL  # noqa: E402
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
from app.infrastructure.repositories.patient_assignment_repository import (  # noqa: E402
    SQLAlchemyPatientAssignmentRepository,
)
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository  # noqa: E402
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository  # noqa: E402


def _config_from_env() -> DemoOrganizationFixtureSeedConfig:
    return DemoOrganizationFixtureSeedConfig(
        organization_slug=os.getenv("DEMO_ORGANIZATION_SLUG", DEMO_ORGANIZATION_SLUG),
        clinic_admin_email=os.getenv("DEMO_CLINIC_ADMIN_EMAIL", DEMO_CLINIC_ADMIN_EMAIL),
        demo_doctor_email=os.getenv("DEMO_DOCTOR_EMAIL", DEMO_DOCTOR_EMAIL),
        patient_first_name=os.getenv("DEMO_PATIENT_FIRST_NAME", DEMO_PATIENT_FIRST_NAME),
        patient_last_name=os.getenv("DEMO_PATIENT_LAST_NAME", DEMO_PATIENT_LAST_NAME),
        patient_gender=os.getenv("DEMO_PATIENT_GENDER", DEMO_PATIENT_GENDER),
        patient_seed_marker=os.getenv("DEMO_PATIENT_SEED_MARKER", DEMO_PATIENT_SEED_MARKER),
    )


def _ensure_database_url(settings: Settings) -> None:
    if not str(settings.database_url).strip():
        print("DATABASE_URL is required.", file=sys.stderr)
        sys.exit(1)


async def _run() -> int:
    settings = get_settings()
    _ensure_database_url(settings)
    config = _config_from_env()

    reset_database_engine()
    session_factory = get_session_factory(settings)
    try:
        async with session_factory() as session:
            result = await seed_demo_organization_fixtures(
                user_repository=SQLAlchemyUserRepository(session),
                organization_repository=SQLAlchemyOrganizationRepository(session),
                membership_repository=SQLAlchemyOrganizationMembershipRepository(session),
                patient_repository=SQLAlchemyPatientRepository(session),
                assignment_repository=SQLAlchemyPatientAssignmentRepository(session),
                config=config,
            )
            await session.commit()
    finally:
        await dispose_engine()

    print(
        "Demo organization fixtures seed finished "
        f"(organization_id={result.organization_id}, "
        f"doctor_user_id={result.doctor_user_id}, patient_id={result.patient_id}, "
        f"created_doctor_membership={result.created_doctor_membership}, "
        f"created_patient={result.created_patient}, "
        f"created_assignment={result.created_assignment})",
    )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()

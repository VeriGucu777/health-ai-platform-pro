#!/usr/bin/env python3
"""Ensure demo doctor user exists with known password (DATABASE_URL required, ops only)."""

from __future__ import annotations

import asyncio
import os
import sys

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.application.seeding.demo_doctor_user_seed import (  # noqa: E402
    DEMO_DOCTOR_EMAIL,
    DEMO_DOCTOR_FIRST_NAME,
    DEMO_DOCTOR_LAST_NAME,
    DEMO_DOCTOR_PASSWORD,
    DemoDoctorUserSeedConfig,
    ensure_demo_doctor_user,
)
from app.core.config import Settings, get_settings  # noqa: E402
from app.infrastructure.database.session import (  # noqa: E402
    dispose_engine,
    get_session_factory,
    reset_database_engine,
)
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository  # noqa: E402


def _config_from_env() -> DemoDoctorUserSeedConfig:
    return DemoDoctorUserSeedConfig(
        email=os.getenv("DEMO_DOCTOR_EMAIL", DEMO_DOCTOR_EMAIL),
        password=os.getenv("DEMO_DOCTOR_PASSWORD", DEMO_DOCTOR_PASSWORD),
        first_name=os.getenv("DEMO_DOCTOR_FIRST_NAME", DEMO_DOCTOR_FIRST_NAME),
        last_name=os.getenv("DEMO_DOCTOR_LAST_NAME", DEMO_DOCTOR_LAST_NAME),
    )


def _ensure_database_url(settings: Settings) -> None:
    if not str(settings.database_url).strip():
        print("DATABASE_URL is required.", file=sys.stderr)
        sys.exit(1)


async def _run() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    _ensure_database_url(settings)
    config = _config_from_env()

    reset_database_engine()
    session_factory = get_session_factory(settings)
    try:
        async with session_factory() as session:
            result = await ensure_demo_doctor_user(
                SQLAlchemyUserRepository(session),
                config=config,
            )
            await session.commit()
    finally:
        await dispose_engine()

    print(
        "Demo doctor user ensure finished "
        f"(user_id={result.user_id}, role={result.role}, "
        f"created_user={result.created_user}, "
        f"password_reset={result.password_reset}, "
        f"activated_user={result.activated_user})",
    )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()

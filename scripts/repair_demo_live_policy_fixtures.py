#!/usr/bin/env python3
"""Analyze/repair demo-live-policy fixtures via DATABASE_URL (ops only)."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.application.seeding.demo_clinic_admin_seed import DEMO_ORGANIZATION_SLUG  # noqa: E402
from app.application.seeding.demo_live_policy_repair import (  # noqa: E402
    repair_demo_live_policy_assignments,
    snapshot_demo_assignments,
)
from app.application.seeding.demo_organization_fixture_seed import DEMO_DOCTOR_EMAIL  # noqa: E402
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
from app.infrastructure.repositories.user_repository import normalize_email  # noqa: E402


def _ensure_database_url(settings: Settings) -> None:
    if not str(settings.database_url).strip():
        print("DATABASE_URL is required.", file=sys.stderr)
        sys.exit(1)


async def _run(*, mode: str, dry_run: bool, confirm_repair: bool) -> int:
    if mode == "repair" and not dry_run and not confirm_repair:
        print(
            "Refusing repair: pass --confirm-repair to commit assignment changes, "
            "or --dry-run to preview.",
            file=sys.stderr,
        )
        return 1

    settings = get_settings()
    _ensure_database_url(settings)
    reset_database_engine()
    session_factory = get_session_factory(settings)

    org_slug = os.getenv("DEMO_ORGANIZATION_SLUG", DEMO_ORGANIZATION_SLUG)
    doctor_email = normalize_email(os.getenv("DEMO_DOCTOR_EMAIL", DEMO_DOCTOR_EMAIL))

    try:
        async with session_factory() as session:
            user_repo = SQLAlchemyUserRepository(session)
            org_repo = SQLAlchemyOrganizationRepository(session)
            membership_repo = SQLAlchemyOrganizationMembershipRepository(session)
            patient_repo = SQLAlchemyPatientRepository(session)
            assignment_repo = SQLAlchemyPatientAssignmentRepository(session)

            org = await org_repo.get_by_slug(org_slug)
            if org is None:
                print(f"Organization slug {org_slug!r} not found.", file=sys.stderr)
                return 1
            doctor = await user_repo.get_by_email(doctor_email)
            if doctor is None:
                print(f"Demo doctor email {doctor_email!r} not found.", file=sys.stderr)
                return 1

            before_policy, before_unassigned = await snapshot_demo_assignments(
                patient_repository=patient_repo,
                assignment_repository=assignment_repo,
                organization_id=org.id,
                doctor_user_id=doctor.id,
            )

            if mode == "analyze" or (mode == "repair" and dry_run):
                print(
                    "Snapshot "
                    f"policy_status={before_policy.status} "
                    f"unassigned_status={before_unassigned.status} "
                    f"dry_run={dry_run}",
                )
                if mode == "repair" and dry_run:
                    would_reactivate = before_policy.status != "active"
                    would_deactivate = before_unassigned.status == "active"
                    print(
                        "Planned "
                        f"policy_reactivate={would_reactivate} "
                        f"unassigned_deactivate={would_deactivate}",
                    )
                await session.rollback()
                return 0

            result = await repair_demo_live_policy_assignments(
                user_repository=user_repo,
                organization_repository=org_repo,
                membership_repository=membership_repo,
                patient_repository=patient_repo,
                assignment_repository=assignment_repo,
            )
            after_policy, after_unassigned = await snapshot_demo_assignments(
                patient_repository=patient_repo,
                assignment_repository=assignment_repo,
                organization_id=org.id,
                doctor_user_id=doctor.id,
            )
            await session.commit()

            print(
                "Repair finished "
                f"policy_before={before_policy.status} policy_after={after_policy.status} "
                f"unassigned_before={before_unassigned.status} unassigned_after={after_unassigned.status} "
                f"policy_reactivated={result.policy_assignment_reactivated} "
                f"unassigned_deactivated={result.unassigned_assignments_deactivated}",
            )
    finally:
        await dispose_engine()

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo live policy fixture DB ops (default: read-only analyze).",
    )
    parser.add_argument(
        "--mode",
        choices=("analyze", "repair"),
        default="analyze",
        help="analyze=snapshot only (default); repair=assignment fix",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With repair: preview without committing.",
    )
    parser.add_argument(
        "--confirm-repair",
        action="store_true",
        help="Required for repair without --dry-run.",
    )
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(
            _run(
                mode=args.mode,
                dry_run=args.dry_run,
                confirm_repair=args.confirm_repair,
            ),
        ),
    )


if __name__ == "__main__":
    main()

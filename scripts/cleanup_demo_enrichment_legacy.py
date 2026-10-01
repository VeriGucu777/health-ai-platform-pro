#!/usr/bin/env python3
"""Analyze or deactivate legacy Task 3 demo enrichment rows (ops only).

Default: read-only ANALYZE (dry-run). Mutation requires --confirm-cleanup.

Legacy rows are soft-deactivated (is_active=false, deleted_at set). Notes are not modified.
No hard DELETE is performed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.application.seeding.demo_clinic_admin_seed import DEMO_ORGANIZATION_SLUG  # noqa: E402
from app.application.seeding.demo_enrichment_legacy_cleanup import (  # noqa: E402
    DemoEnrichmentLegacyCleanupConfig,
    EXPECTED_LEGACY_MEASUREMENT_TOTAL,
    EXPECTED_LEGACY_MEDICAL_RECORD_TOTAL,
    run_demo_enrichment_legacy_cleanup,
)
from app.core.config import Settings, get_settings  # noqa: E402
from app.infrastructure.database.session import (  # noqa: E402
    dispose_engine,
    get_session_factory,
    reset_database_engine,
)
from app.infrastructure.repositories.appointment_repository import (  # noqa: E402
    SQLAlchemyAppointmentRepository,
)
from app.infrastructure.repositories.health_measurement_repository import (  # noqa: E402
    SQLAlchemyHealthMeasurementRepository,
)
from app.infrastructure.repositories.medical_record_repository import (  # noqa: E402
    SQLAlchemyMedicalRecordRepository,
)
from app.infrastructure.repositories.organization_repository import (  # noqa: E402
    SQLAlchemyOrganizationRepository,
)
from app.infrastructure.repositories.patient_assignment_repository import (  # noqa: E402
    SQLAlchemyPatientAssignmentRepository,
)
from app.infrastructure.repositories.patient_consent_repository import (  # noqa: E402
    SQLAlchemyPatientConsentRepository,
)
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository  # noqa: E402
from app.infrastructure.repositories.risk_assessment_history_repository import (  # noqa: E402
    SQLAlchemyRiskAssessmentHistoryRepository,
)


def _ensure_database_url(settings: Settings) -> None:
    if not str(settings.database_url).strip():
        print("DATABASE_URL is required.", file=sys.stderr)
        sys.exit(1)


def _result_to_dict(result) -> dict:
    inv = result.inventory
    return {
        "mode": result.mode,
        "mutated": result.mutated,
        "guard_ok": result.guard.ok,
        "abort_reasons": list(result.abort_reasons or result.guard.abort_reasons),
        "expected_legacy_measurements": EXPECTED_LEGACY_MEASUREMENT_TOTAL,
        "expected_legacy_medical_records": EXPECTED_LEGACY_MEDICAL_RECORD_TOTAL,
        "inventory_notes": inv.notes,
        "legacy_measurements_active": inv.legacy_measurements_active,
        "legacy_medical_records_active": inv.legacy_medical_records_active,
        "v2_measurements": inv.v2_measurements,
        "v2_medical_records": inv.v2_medical_records,
        "non_task3_measurements": inv.non_task3_measurements,
        "non_task3_medical_records": inv.non_task3_medical_records,
        "patients": [
            {
                "key": row.patient_key,
                "patient_id": str(row.patient_id),
                "marker_ok": row.marker_ok,
                "legacy_measurements_active": row.legacy_measurements_active,
                "legacy_medical_records_active": row.legacy_medical_records_active,
                "v2_measurements": row.v2_measurements,
                "v2_medical_records": row.v2_medical_records,
                "appointments": row.appointments,
                "risk_history": row.risk_history,
                "assignments": row.assignments,
                "consents": row.consents,
                "patient_is_active": row.patient_is_active,
            }
            for row in inv.patient_rows
        ],
        "deactivated_measurements": result.deactivated_measurements,
        "deactivated_medical_records": result.deactivated_medical_records,
        "post_verify_ok": result.post_verify_ok,
        "protected_before": (
            None
            if result.protected_before is None
            else {
                "appointments": result.protected_before.appointments,
                "risk_history": result.protected_before.risk_history,
                "assignments": result.protected_before.assignments,
                "consents": result.protected_before.consents,
            }
        ),
        "protected_after": (
            None
            if result.protected_after is None
            else {
                "appointments": result.protected_after.appointments,
                "risk_history": result.protected_after.risk_history,
                "assignments": result.protected_after.assignments,
                "consents": result.protected_after.consents,
            }
        ),
    }


async def _run(*, confirm_cleanup: bool) -> int:
    get_settings.cache_clear()
    settings = get_settings()
    _ensure_database_url(settings)

    org_slug = os.getenv("DEMO_ORGANIZATION_SLUG", DEMO_ORGANIZATION_SLUG)
    allow_test_ids = os.getenv("DEMO_CLEANUP_ALLOW_TEST_IDS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    config = DemoEnrichmentLegacyCleanupConfig(
        organization_slug=org_slug,
        verify_production_patient_ids=not allow_test_ids,
    )

    if confirm_cleanup and not allow_test_ids:
        print(
            "Cleanup will soft-deactivate legacy demo rows (is_active=false). "
            "Pass --confirm-cleanup only after ANALYZE guard_ok=true.",
            file=sys.stderr,
        )

    reset_database_engine()
    session_factory = get_session_factory(settings)
    try:
        async with session_factory() as session:
            kwargs = {
                "organization_repository": SQLAlchemyOrganizationRepository(session),
                "patient_repository": SQLAlchemyPatientRepository(session),
                "measurement_repository": SQLAlchemyHealthMeasurementRepository(session),
                "medical_record_repository": SQLAlchemyMedicalRecordRepository(session),
                "appointment_repository": SQLAlchemyAppointmentRepository(session),
                "risk_history_repository": SQLAlchemyRiskAssessmentHistoryRepository(session),
                "assignment_repository": SQLAlchemyPatientAssignmentRepository(session),
                "consent_repository": SQLAlchemyPatientConsentRepository(session),
                "config": config,
                "confirm_cleanup": confirm_cleanup,
            }
            result = await run_demo_enrichment_legacy_cleanup(**kwargs)
            if confirm_cleanup and result.mutated:
                if result.post_verify_ok:
                    await session.commit()
                else:
                    await session.rollback()
                    result = DemoEnrichmentLegacyCleanupResultShim(result)
            elif confirm_cleanup and not result.mutated:
                await session.rollback()
            else:
                await session.rollback()
    finally:
        await dispose_engine()

    payload = _result_to_dict(result)
    print(json.dumps(payload, indent=2))
    if confirm_cleanup and result.mode == "cleanup_aborted":
        return 1
    if confirm_cleanup and result.mutated and not result.post_verify_ok:
        return 1
    return 0


class DemoEnrichmentLegacyCleanupResultShim:
    """Wrap failed post-verify cleanup for JSON output without mutating session."""

    def __init__(self, inner) -> None:
        self.__dict__.update(inner.__dict__)
        self.mode = "cleanup_aborted"
        self.mutated = False
        self.abort_reasons = ("post_verify_failed",)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Legacy Task 3 demo enrichment cleanup (default: analyze only).",
    )
    parser.add_argument(
        "--confirm-cleanup",
        action="store_true",
        help="Apply soft-delete deactivation after fail-safe guards pass.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(confirm_cleanup=args.confirm_cleanup)))


if __name__ == "__main__":
    main()

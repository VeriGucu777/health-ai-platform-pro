#!/usr/bin/env python3
"""Analyze or apply demo clinical enrichment (DATABASE_URL required for DB mode)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.application.seeding.demo_clinical_enrichment import (  # noqa: E402
    DemoClinicalEnrichmentConfig,
    analyze_demo_clinical_enrichment,
    seed_demo_clinical_enrichment,
)
from app.application.seeding.demo_doctor_user_seed import DEMO_DOCTOR_EMAIL  # noqa: E402
from app.application.seeding.demo_clinic_admin_seed import (  # noqa: E402
    DEMO_CLINIC_ADMIN_EMAIL,
    DEMO_ORGANIZATION_SLUG,
)
from app.application.seeding.demo_doctor_b_user_seed import DEFAULT_DEMO_DOCTOR_B_EMAIL  # noqa: E402
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
from app.infrastructure.repositories.organization_membership_repository import (  # noqa: E402
    SQLAlchemyOrganizationMembershipRepository,
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
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository  # noqa: E402


def _config_from_env() -> DemoClinicalEnrichmentConfig:
    return DemoClinicalEnrichmentConfig(
        organization_slug=os.getenv("DEMO_ORGANIZATION_SLUG", DEMO_ORGANIZATION_SLUG),
        clinic_admin_email=os.getenv("DEMO_CLINIC_ADMIN_EMAIL", DEMO_CLINIC_ADMIN_EMAIL),
        doctor_a_email=os.getenv("DEMO_DOCTOR_EMAIL", DEMO_DOCTOR_EMAIL),
        doctor_b_email=os.getenv("DEMO_DOCTOR_B_EMAIL", DEFAULT_DEMO_DOCTOR_B_EMAIL),
        doctor_b_password=os.getenv("DEMO_DOCTOR_B_PASSWORD") or None,
        doctor_b_display_name=os.getenv("DEMO_DOCTOR_B_DISPLAY_NAME", "Demo Doctor Two"),
        doctor_a_password=os.getenv("DEMO_DOCTOR_PASSWORD") or None,
    )


def _ensure_database_url(settings: Settings) -> None:
    if not str(settings.database_url).strip():
        print("DATABASE_URL is required.", file=sys.stderr)
        sys.exit(1)


def _result_to_dict(result) -> dict:
    return {
        "organization_id": str(result.organization_id),
        "doctor_a_user_id": str(result.doctor_a_user_id),
        "doctor_b_user_id": (
            str(result.doctor_b_user_id) if result.doctor_b_user_id is not None else None
        ),
        "doctor_b_status": result.doctor_b_status,
        "patient_ids": {k: str(v) for k, v in result.patient_ids.items()},
        "created_patients": result.created_patients,
        "counts": {
            key: {
                "measurements": counts.measurements,
                "medical_records": counts.medical_records,
                "appointments": counts.appointments,
                "risk_history": counts.risk_history,
                "consent_granted": counts.consent_granted,
                "assignment_active": counts.assignment_active,
            }
            for key, counts in result.counts.items()
        },
        "mutate": result.mutate,
    }


async def _run(*, confirm_seed: bool) -> int:
    get_settings.cache_clear()
    settings = get_settings()
    _ensure_database_url(settings)
    config = _config_from_env()

    if confirm_seed and not config.doctor_b_password:
        print(
            "DEMO_DOCTOR_B_PASSWORD is required with --confirm-seed.",
            file=sys.stderr,
        )
        return 1

    reset_database_engine()
    session_factory = get_session_factory(settings)
    try:
        async with session_factory() as session:
            kwargs = {
                "user_repository": SQLAlchemyUserRepository(session),
                "organization_repository": SQLAlchemyOrganizationRepository(session),
                "membership_repository": SQLAlchemyOrganizationMembershipRepository(session),
                "patient_repository": SQLAlchemyPatientRepository(session),
                "assignment_repository": SQLAlchemyPatientAssignmentRepository(session),
                "consent_repository": SQLAlchemyPatientConsentRepository(session),
                "measurement_repository": SQLAlchemyHealthMeasurementRepository(session),
                "medical_record_repository": SQLAlchemyMedicalRecordRepository(session),
                "appointment_repository": SQLAlchemyAppointmentRepository(session),
                "risk_history_repository": SQLAlchemyRiskAssessmentHistoryRepository(session),
                "config": config,
            }
            if confirm_seed:
                result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
                await session.commit()
            else:
                result = await analyze_demo_clinical_enrichment(**kwargs)
    finally:
        await dispose_engine()

    print(json.dumps(_result_to_dict(result), indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo clinical enrichment (default: analyze/dry-run JSON report).",
    )
    parser.add_argument(
        "--confirm-seed",
        action="store_true",
        help="Apply idempotent enrichment (requires DEMO_DOCTOR_B_PASSWORD).",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(confirm_seed=args.confirm_seed)))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Analyze or soft-deactivate the mis-assigned A1 demo stroke risk history row.

Default: read-only ANALYZE (dry-run). Mutation requires --confirm-cleanup.

Only row d547f028-2425-4247-918d-acccfc53c99a is targeted (is_active=false, deleted_at set).
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

from app.application.seeding.demo_risk_history_cleanup import (  # noqa: E402
    A1_WRONG_STROKE_RISK_ID,
    DemoRiskHistoryCleanupConfig,
    run_demo_risk_history_cleanup,
)
from app.core.config import Settings, get_settings  # noqa: E402
from app.infrastructure.database.session import (  # noqa: E402
    dispose_engine,
    get_session_factory,
    reset_database_engine,
)
from app.infrastructure.repositories.risk_assessment_history_repository import (  # noqa: E402
    SQLAlchemyRiskAssessmentHistoryRepository,
)


def _ensure_database_url(settings: Settings) -> None:
    if not str(settings.database_url).strip():
        print("DATABASE_URL is required.", file=sys.stderr)
        sys.exit(1)


def _result_to_dict(result) -> dict:
    def _counts(c):
        if c is None:
            return None
        return {
            "a1_active": c.a1_active,
            "a2_active": c.a2_active,
            "b1_active": c.b1_active,
            "b2_active": c.b2_active,
            "canonical_active": c.canonical_active,
            "legacy_diabetes_active": c.legacy_diabetes_active,
            "target_stroke_active": c.target_stroke_active,
        }

    return {
        "mode": result.mode,
        "mutated": result.mutated,
        "target_risk_id": str(A1_WRONG_STROKE_RISK_ID),
        "guard_ok": result.guard.ok,
        "abort_reasons": list(result.abort_reasons or result.guard.abort_reasons),
        "protected_before": _counts(result.protected_before),
        "protected_after": _counts(result.protected_after),
    }


async def _run(confirm_cleanup: bool, *, verify_production_ids: bool) -> None:
    settings = get_settings()
    _ensure_database_url(settings)
    reset_database_engine()
    session_factory = get_session_factory(settings)
    try:
        async with session_factory() as session:
            repo = SQLAlchemyRiskAssessmentHistoryRepository(session)
            result = await run_demo_risk_history_cleanup(
                risk_history_repository=repo,
                config=DemoRiskHistoryCleanupConfig(verify_production_ids=verify_production_ids),
                confirm_cleanup=confirm_cleanup,
            )
            if result.mutated:
                await session.commit()
            else:
                await session.rollback()
        print(json.dumps(_result_to_dict(result), indent=2))
        if result.mode in ("cleanup_aborted", "cleanup_verify_failed"):
            sys.exit(2)
    finally:
        await dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-cleanup",
        action="store_true",
        help="Soft-deactivate the guarded A1 stroke risk row (default is analyze only).",
    )
    parser.add_argument(
        "--skip-production-id-checks",
        action="store_true",
        help="Do not require production demo patient/risk UUID inventory counts.",
    )
    args = parser.parse_args()
    asyncio.run(
        _run(
            args.confirm_cleanup,
            verify_production_ids=not args.skip_production_id_checks,
        ),
    )


if __name__ == "__main__":
    main()

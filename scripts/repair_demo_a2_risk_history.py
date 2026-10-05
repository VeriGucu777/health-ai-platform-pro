#!/usr/bin/env python3
"""Analyze or repair A2 canonical demo heart_disease risk history (ops only).

Default: read-only ANALYZE. Mutation requires --confirm-repair.
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

from app.application.seeding.demo_a2_canonical_risk_repair import (  # noqa: E402
    run_demo_a2_canonical_risk_repair,
)
from app.core.config import get_settings  # noqa: E402
from app.infrastructure.database.session import (  # noqa: E402
    dispose_engine,
    get_session_factory,
    reset_database_engine,
)
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository  # noqa: E402
from app.infrastructure.repositories.risk_assessment_history_repository import (  # noqa: E402
    SQLAlchemyRiskAssessmentHistoryRepository,
)


async def _run(*, confirm_repair: bool) -> None:
    settings = get_settings()
    if not str(settings.database_url).strip():
        print("DATABASE_URL is required.", file=sys.stderr)
        sys.exit(1)
    reset_database_engine()
    session_factory = get_session_factory(settings)
    try:
        async with session_factory() as session:
            result = await run_demo_a2_canonical_risk_repair(
                patient_repository=SQLAlchemyPatientRepository(session),
                risk_history_repository=SQLAlchemyRiskAssessmentHistoryRepository(session),
                confirm_repair=confirm_repair,
            )
            if result.mutated:
                await session.commit()
            else:
                await session.rollback()
        print(
            json.dumps(
                {
                    "mode": result.mode,
                    "guard_ok": result.guard.ok,
                    "abort_reasons": result.guard.abort_reasons,
                    "record_id": result.record_id,
                    "would_update": result.would_update,
                    "mutated": result.mutated,
                    "before_score": result.before_score,
                    "before_risk_level": result.before_risk_level,
                    "after_score": result.after_score,
                    "after_risk_level": result.after_risk_level,
                },
                indent=2,
            ),
        )
        if result.mode == "repair_aborted" or not result.guard.ok:
            sys.exit(2)
    finally:
        await dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-repair", action="store_true")
    args = parser.parse_args()
    asyncio.run(_run(confirm_repair=args.confirm_repair))


if __name__ == "__main__":
    main()

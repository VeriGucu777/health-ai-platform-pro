"""PostgreSQL migration tests for risk_assessment_history soft-delete columns."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, inspect, text

from tests.integration.support.database import run_alembic_downgrade, run_alembic_upgrade

MIGRATION_REVISION = "s8t9u0v1w2x3"
PREVIOUS_REVISION = "r7s8t9u0v1w2"


def test_risk_history_soft_delete_columns_upgrade_and_downgrade(integration_database_urls):
    sync_url = integration_database_urls.sync_url
    run_alembic_upgrade(sync_url, MIGRATION_REVISION)
    engine = create_engine(sync_url)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("risk_assessment_history")}
    assert "is_active" in columns
    assert "deleted_at" in columns
    engine.dispose()

    run_alembic_downgrade(sync_url, PREVIOUS_REVISION)
    pre_user_id = uuid.uuid4()
    pre_patient_id = uuid.uuid4()
    pre_row_id = uuid.uuid4()
    engine = create_engine(sync_url)
    now = datetime.now(UTC)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, first_name, last_name, role, "
                "is_verified, is_active, token_version, created_at, updated_at) "
                "VALUES (:id, :email, 'hash', 'Pre', 'Migration', 'doctor', true, true, 0, :now, :now)",
            ),
            {"id": pre_user_id, "email": f"pre-risk-{pre_user_id.hex[:8]}@example.test", "now": now},
        )
        conn.execute(
            text(
                "INSERT INTO patients (id, owner_id, first_name, last_name, date_of_birth, gender, "
                "is_active, created_at, updated_at) "
                "VALUES (:id, :owner_id, 'Pre', 'Patient', '1990-01-01', 'female', true, :now, :now)",
            ),
            {"id": pre_patient_id, "owner_id": pre_user_id, "now": now},
        )
        conn.execute(
            text(
                "INSERT INTO risk_assessment_history "
                "(id, patient_id, assessment_type, assessment_status, model_kind, model_version, "
                "evaluated_by_user_id, evaluated_at, created_at, updated_at) "
                "VALUES (:id, :patient_id, 'diabetes', 'completed', 'rule_based', 'rule_based_v1', "
                ":evaluator, :now, :now, :now)",
            ),
            {
                "id": pre_row_id,
                "patient_id": pre_patient_id,
                "evaluator": pre_user_id,
                "now": now,
            },
        )
    engine.dispose()

    run_alembic_upgrade(sync_url, MIGRATION_REVISION)
    engine = create_engine(sync_url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT is_active, deleted_at FROM risk_assessment_history WHERE id = :id",
            ),
            {"id": pre_row_id},
        ).one()
        assert row.is_active is True
        assert row.deleted_at is None
    engine.dispose()

    run_alembic_downgrade(sync_url, PREVIOUS_REVISION)
    engine = create_engine(sync_url)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("risk_assessment_history")}
    assert "is_active" not in columns
    assert "deleted_at" not in columns
    engine.dispose()

    run_alembic_upgrade(sync_url, "head")

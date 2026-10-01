"""PostgreSQL migration tests for clinical child soft-delete columns."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, inspect, text

from tests.integration.support.database import run_alembic_downgrade, run_alembic_upgrade

MIGRATION_REVISION = "r7s8t9u0v1w2"
PREVIOUS_REVISION = "q6r7s8t9u0v1"


def test_clinical_child_soft_delete_columns_upgrade_and_downgrade(integration_database_urls):
    sync_url = integration_database_urls.sync_url
    run_alembic_upgrade(sync_url, MIGRATION_REVISION)
    engine = create_engine(sync_url)
    inspector = inspect(engine)
    for table in ("health_measurements", "medical_records"):
        columns = {col["name"] for col in inspector.get_columns(table)}
        assert "is_active" in columns
        assert "deleted_at" in columns
    engine.dispose()

    run_alembic_downgrade(sync_url, PREVIOUS_REVISION)
    pre_user_id = uuid.uuid4()
    pre_patient_id = uuid.uuid4()
    pre_meas_id = uuid.uuid4()
    engine = create_engine(sync_url)
    now = datetime.now(UTC)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, first_name, last_name, role, "
                "is_verified, is_active, token_version, created_at, updated_at) "
                "VALUES (:id, :email, 'hash', 'Pre', 'Migration', 'doctor', true, true, 0, :now, :now)",
            ),
            {"id": pre_user_id, "email": f"pre-mig-{pre_user_id.hex[:8]}@example.test", "now": now},
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
                "INSERT INTO health_measurements (id, owner_id, patient_id, measured_at, created_at, updated_at) "
                "VALUES (:id, :owner_id, :patient_id, :now, :now, :now)",
            ),
            {
                "id": pre_meas_id,
                "owner_id": pre_user_id,
                "patient_id": pre_patient_id,
                "now": now,
            },
        )
    engine.dispose()

    run_alembic_upgrade(sync_url, MIGRATION_REVISION)
    engine = create_engine(sync_url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT is_active, deleted_at FROM health_measurements WHERE id = :id",
            ),
            {"id": pre_meas_id},
        ).one()
        assert row.is_active is True
        assert row.deleted_at is None
    engine.dispose()

    run_alembic_downgrade(sync_url, PREVIOUS_REVISION)
    engine = create_engine(sync_url)
    inspector = inspect(engine)
    for table in ("health_measurements", "medical_records"):
        columns = {col["name"] for col in inspector.get_columns(table)}
        assert "is_active" not in columns
        assert "deleted_at" not in columns
    engine.dispose()

    run_alembic_upgrade(sync_url, "head")

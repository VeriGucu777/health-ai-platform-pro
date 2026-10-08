"""PostgreSQL migration and constraint tests for clinical encounter shell."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.support.database import run_alembic_downgrade, run_alembic_upgrade

MIGRATION_REVISION = "t9u0v1w2x3y4"
PREVIOUS_REVISION = "s8t9u0v1w2x3"


def _seed_org_patient_user(conn, *, org_id, patient_id, user_id, email_suffix: str) -> None:
    now = datetime.now(UTC)
    conn.execute(
        text(
            "INSERT INTO users (id, email, hashed_password, first_name, last_name, role, "
            "is_verified, is_active, token_version, created_at, updated_at) "
            "VALUES (:id, :email, 'hash', 'Enc', 'Doctor', 'doctor', true, true, 0, :now, :now)",
        ),
        {"id": user_id, "email": f"enc-{email_suffix}@example.test", "now": now},
    )
    conn.execute(
        text(
            "INSERT INTO organizations (id, name, is_active, created_at, updated_at) "
            "VALUES (:id, 'Test Org', true, :now, :now)",
        ),
        {"id": org_id, "now": now},
    )
    conn.execute(
        text(
            "INSERT INTO patients (id, owner_id, organization_id, first_name, last_name, "
            "date_of_birth, gender, is_active, created_at, updated_at) "
            "VALUES (:id, :owner_id, :org_id, 'Pat', 'One', '1990-01-01', 'female', true, :now, :now)",
        ),
        {"id": patient_id, "owner_id": user_id, "org_id": org_id, "now": now},
    )


def test_clinical_encounter_migration_upgrade_downgrade_reupgrade(integration_database_urls) -> None:
    sync_url = integration_database_urls.sync_url
    run_alembic_upgrade(sync_url, MIGRATION_REVISION)
    engine = create_engine(sync_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    for name in (
        "clinical_encounters",
        "encounter_complaints",
        "encounter_findings",
        "encounter_question_responses",
        "encounter_final_summaries",
    ):
        assert name in tables
    hm_cols = {c["name"] for c in inspector.get_columns("health_measurements")}
    mr_cols = {c["name"] for c in inspector.get_columns("medical_records")}
    assert "encounter_id" in hm_cols
    assert "encounter_id" in mr_cols
    engine.dispose()

    run_alembic_downgrade(sync_url, PREVIOUS_REVISION)
    engine = create_engine(sync_url)
    inspector = inspect(engine)
    assert "clinical_encounters" not in inspector.get_table_names()
    engine.dispose()

    run_alembic_upgrade(sync_url, MIGRATION_REVISION)


def test_two_active_encounters_same_patient_org_rejected(integration_database_urls) -> None:
    sync_url = integration_database_urls.sync_url
    run_alembic_upgrade(sync_url, "head")
    org_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    user_id = uuid.uuid4()
    enc_a = uuid.uuid4()
    enc_b = uuid.uuid4()
    now = datetime.now(UTC)
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        _seed_org_patient_user(conn, org_id=org_id, patient_id=patient_id, user_id=user_id, email_suffix="a")
        conn.execute(
            text(
                "INSERT INTO clinical_encounters (id, patient_id, organization_id, clinician_user_id, "
                "specialty_key, status, locale, version, is_active, created_at, updated_at) "
                "VALUES (:id, :pid, :oid, :uid, 'cardiology', 'active', 'en', 1, true, :now, :now)",
            ),
            {"id": enc_a, "pid": patient_id, "oid": org_id, "uid": user_id, "now": now},
        )
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO clinical_encounters (id, patient_id, organization_id, clinician_user_id, "
                    "specialty_key, status, locale, version, is_active, created_at, updated_at) "
                    "VALUES (:id, :pid, :oid, :uid, 'cardiology', 'active', 'en', 1, true, :now, :now)",
                ),
                {"id": enc_b, "pid": patient_id, "oid": org_id, "uid": user_id, "now": now},
            )
    engine.dispose()


def test_finalized_and_active_allowed_for_same_patient(integration_database_urls) -> None:
    sync_url = integration_database_urls.sync_url
    run_alembic_upgrade(sync_url, "head")
    org_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        _seed_org_patient_user(conn, org_id=org_id, patient_id=patient_id, user_id=user_id, email_suffix="b")
        conn.execute(
            text(
                "INSERT INTO clinical_encounters (id, patient_id, organization_id, clinician_user_id, "
                "specialty_key, status, locale, version, is_active, created_at, updated_at) "
                "VALUES (:id1, :pid, :oid, :uid, 'cardiology', 'finalized', 'en', 1, true, :now, :now), "
                "(:id2, :pid, :oid, :uid, 'cardiology', 'active', 'en', 1, true, :now, :now)",
            ),
            {
                "id1": uuid.uuid4(),
                "id2": uuid.uuid4(),
                "pid": patient_id,
                "oid": org_id,
                "uid": user_id,
                "now": now,
            },
        )
    engine.dispose()


def test_duplicate_appointment_id_rejected(integration_database_urls) -> None:
    sync_url = integration_database_urls.sync_url
    run_alembic_upgrade(sync_url, "head")
    org_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    user_id = uuid.uuid4()
    appt_id = uuid.uuid4()
    now = datetime.now(UTC)
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        _seed_org_patient_user(conn, org_id=org_id, patient_id=patient_id, user_id=user_id, email_suffix="c")
        conn.execute(
            text(
                "INSERT INTO appointments (id, owner_id, patient_id, appointment_date, appointment_type, "
                "status, created_at, updated_at) "
                "VALUES (:id, :uid, :pid, :now, 'visit', 'scheduled', :now, :now)",
            ),
            {"id": appt_id, "uid": user_id, "pid": patient_id, "now": now},
        )
        conn.execute(
            text(
                "INSERT INTO clinical_encounters (id, patient_id, organization_id, clinician_user_id, "
                "specialty_key, status, locale, appointment_id, version, is_active, created_at, updated_at) "
                "VALUES (:id1, :pid, :oid, :uid, 'cardiology', 'draft', 'en', :appt, 1, true, :now, :now)",
            ),
            {
                "id1": uuid.uuid4(),
                "pid": patient_id,
                "oid": org_id,
                "uid": user_id,
                "appt": appt_id,
                "now": now,
            },
        )
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO clinical_encounters (id, patient_id, organization_id, clinician_user_id, "
                    "specialty_key, status, locale, appointment_id, version, is_active, created_at, updated_at) "
                    "VALUES (:id2, :pid, :oid, :uid, 'cardiology', 'draft', 'en', :appt, 1, true, :now, :now)",
                ),
                {
                    "id2": uuid.uuid4(),
                    "pid": patient_id,
                    "oid": org_id,
                    "uid": user_id,
                    "appt": appt_id,
                    "now": now,
                },
            )
    engine.dispose()

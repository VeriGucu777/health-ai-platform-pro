"""PostgreSQL integration tests for email verification migration."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from tests.integration.support.database import (
    assert_safe_integration_url,
    run_alembic_downgrade,
    run_alembic_upgrade,
)

PRE_EMAIL_REVISION = "n3o4p5q6r7s8"
EMAIL_REVISION = "o4p5q6r7s8t0"


@pytest.fixture
def email_migration_db(integration_database_urls):
    """Empty DB upgraded to pre-email revision for migration testing."""
    sync_url = integration_database_urls.sync_url
    assert_safe_integration_url(sync_url)
    run_alembic_downgrade(sync_url, "base")
    run_alembic_upgrade(sync_url, PRE_EMAIL_REVISION)
    yield sync_url
    run_alembic_upgrade(sync_url, "head")


def test_email_verification_migration_upgrade_backfill_and_schema(email_migration_db: str) -> None:
    user_id = uuid.uuid4()
    engine = create_engine(email_migration_db, poolclass=NullPool)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO users (
                    id, email, hashed_password, first_name, last_name, role,
                    is_active, is_verified, token_version, created_at, updated_at
                ) VALUES (
                    :id, :email, :hash, 'Pre', 'Migration', 'doctor',
                    true, false, 0, NOW(), NOW()
                )
                """,
            ),
            {
                "id": user_id,
                "email": "pre-migration-unverified@example.com",
                "hash": "$2b$12$testhashplaceholderxxxxxxxxxxxxxxxxxxxxxx",
            },
        )

    run_alembic_upgrade(email_migration_db, EMAIL_REVISION)

    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT is_verified, email_verified_at FROM users WHERE id = :id",
            ),
            {"id": user_id},
        ).one()
        assert row.is_verified is True
        assert row.email_verified_at is not None

        tables = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
                ),
            )
        }
        assert "email_verification_tokens" in tables

        columns = {
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'email_verification_tokens'
                    """,
                ),
            )
        }
        assert {"token_hash", "user_id", "expires_at", "used_at", "superseded_at"}.issubset(columns)

        fk = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE table_name = 'email_verification_tokens'
                  AND constraint_type = 'FOREIGN KEY'
                """,
            ),
        ).scalar_one()
        assert fk >= 1

    run_alembic_downgrade(email_migration_db, PRE_EMAIL_REVISION)
    with engine.connect() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
                ),
            )
        }
        assert "email_verification_tokens" not in tables
        cols = {
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'users'
                    """,
                ),
            )
        }
        assert "email_verified_at" not in cols

    run_alembic_upgrade(email_migration_db, "head")
    with engine.connect() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
                ),
            )
        }
        assert "email_verification_tokens" in tables

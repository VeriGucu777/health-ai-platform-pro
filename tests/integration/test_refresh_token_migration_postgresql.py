"""PostgreSQL integration tests for user_refresh_sessions migration."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from tests.integration.support.database import (
    assert_safe_integration_url,
    run_alembic_current,
    run_alembic_downgrade,
    run_alembic_upgrade,
)

PRE_REFRESH_SESSIONS_REVISION = "o4p5q6r7s8t0"
REFRESH_SESSIONS_REVISION = "q6r7s8t9u0v1"


@pytest.fixture
def refresh_migration_db(integration_database_urls):
    sync_url = integration_database_urls.sync_url
    assert_safe_integration_url(sync_url)
    run_alembic_downgrade(sync_url, "base")
    run_alembic_upgrade(sync_url, PRE_REFRESH_SESSIONS_REVISION)
    yield sync_url
    run_alembic_upgrade(sync_url, "head")


def test_user_refresh_sessions_migration(refresh_migration_db: str) -> None:
    user_id = uuid.uuid4()
    engine = create_engine(refresh_migration_db, poolclass=NullPool)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO users (
                    id, email, hashed_password, first_name, last_name, role,
                    is_active, is_verified, token_version, created_at, updated_at
                ) VALUES (
                    :id, :email, :hash, 'Refresh', 'User', 'patient',
                    true, true, 0, NOW(), NOW()
                )
                """,
            ),
            {
                "id": user_id,
                "email": "refresh-migration@example.com",
                "hash": "$2b$12$testhashplaceholderxxxxxxxxxxxxxxxxxxxxxx",
            },
        )

    run_alembic_upgrade(refresh_migration_db, REFRESH_SESSIONS_REVISION)

    with engine.connect() as conn:
        user_columns = {
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'users'
                    """,
                ),
            )
        }
        assert "refresh_token_id_hash" not in user_columns

        tables = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
                ),
            )
        }
        assert "user_refresh_sessions" in tables

        fks = conn.execute(
            text(
                """
                SELECT tc.constraint_name, ccu.table_name AS foreign_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_name = 'user_refresh_sessions'
                """,
            ),
        ).all()
        assert any(fk.foreign_table == "users" for fk in fks)

        indexes = conn.execute(
            text(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'user_refresh_sessions'",
            ),
        ).all()
        index_names = {row.indexname for row in indexes}
        assert "ix_user_refresh_sessions_user_id" in index_names
        assert any("user_refresh_sessions" in name for name in index_names)

    run_alembic_downgrade(refresh_migration_db, PRE_REFRESH_SESSIONS_REVISION)
    with engine.connect() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
                ),
            )
        }
        assert "user_refresh_sessions" not in tables

    run_alembic_upgrade(refresh_migration_db, "head")
    assert run_alembic_current(refresh_migration_db) == REFRESH_SESSIONS_REVISION

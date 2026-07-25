"""Alembic migration integration tests."""

from tests.integration.support.database import (
    EXPECTED_TABLES,
    list_public_tables_sync,
    run_alembic_downgrade,
    run_alembic_upgrade,
)


def test_migrations_from_empty_database_to_head(integration_database_urls):
    """Upgrade from base on an empty database creates the expected schema."""
    run_alembic_downgrade(integration_database_urls.sync_url, "base")
    run_alembic_upgrade(integration_database_urls.sync_url, "head")

    tables = list_public_tables_sync(integration_database_urls.sync_url)
    assert EXPECTED_TABLES.issubset(tables)

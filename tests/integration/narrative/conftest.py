"""External narrative integration fixtures."""

from __future__ import annotations

import os

import pytest

from app.core.config import Settings


def external_live_settings_configured() -> bool:
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        CLINICAL_NARRATIVE_PROVIDER="external",
        CLINICAL_NARRATIVE_EXTERNAL_BASE_URL=os.environ.get("CLINICAL_NARRATIVE_EXTERNAL_BASE_URL", ""),
        CLINICAL_NARRATIVE_EXTERNAL_API_KEY=os.environ.get("CLINICAL_NARRATIVE_EXTERNAL_API_KEY", ""),
        CLINICAL_NARRATIVE_EXTERNAL_MODEL=os.environ.get("CLINICAL_NARRATIVE_EXTERNAL_MODEL", ""),
    )
    return (
        settings.clinical_narrative_external_api_key.strip() != ""
        and settings.clinical_narrative_external_base_url.strip() != ""
        and settings.clinical_narrative_external_model.strip() != ""
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "tests/integration/narrative" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            if "live" in item.nodeid:
                item.add_marker(pytest.mark.external_narrative_live)


@pytest.fixture(scope="session", autouse=True)
def require_live_smoke_credentials():
    if os.environ.get("CLINICAL_NARRATIVE_LIVE_SMOKE", "").strip() != "1":
        return
    if not external_live_settings_configured():
        pytest.fail(
            "CLINICAL_NARRATIVE_LIVE_SMOKE=1 but external provider env is incomplete. "
            "Set CLINICAL_NARRATIVE_EXTERNAL_BASE_URL, CLINICAL_NARRATIVE_EXTERNAL_API_KEY, "
            "and CLINICAL_NARRATIVE_EXTERNAL_MODEL (no fake fallback).",
        )

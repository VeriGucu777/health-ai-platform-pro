"""Smoke tests for scripts/cleanup_demo_risk_history.py bootstrap."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "cleanup_demo_risk_history.py"


def _load_cleanup_script_module():
    spec = importlib.util.spec_from_file_location("cleanup_demo_risk_history", _SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cleanup_script_cli_help_smoke():
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0
    assert "--confirm-cleanup" in result.stdout


@pytest.mark.asyncio
async def test_run_analyze_calls_reset_database_engine_without_arguments(monkeypatch):
    mod = _load_cleanup_script_module()
    reset_mock = MagicMock()
    monkeypatch.setattr(mod, "reset_database_engine", reset_mock)
    monkeypatch.setattr(mod, "get_settings", lambda: MagicMock(database_url="postgresql+asyncpg://x"))

    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    class _SessionCtx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(mod, "get_session_factory", lambda _settings: (lambda: _SessionCtx()))
    monkeypatch.setattr(mod, "dispose_engine", AsyncMock())

    from app.application.seeding.demo_risk_history_cleanup import (
        DemoRiskHistoryCleanupGuard,
        DemoRiskHistoryCleanupResult,
    )

    async def _fake_cleanup(**_kwargs):
        return DemoRiskHistoryCleanupResult(
            mode="analyze",
            guard=DemoRiskHistoryCleanupGuard(ok=True),
            mutated=False,
        )

    monkeypatch.setattr(mod, "run_demo_risk_history_cleanup", _fake_cleanup)

    await mod._run(False, verify_production_ids=False)

    reset_mock.assert_called_once_with()
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()

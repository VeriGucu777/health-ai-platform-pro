"""Audit log model and migration smoke tests."""

from pathlib import Path

from app.infrastructure.database.models import AuditLogModel
from app.infrastructure.database.models.audit_log import AuditLogModel as AuditLogModelDirect


def test_audit_log_model_import() -> None:
    assert AuditLogModel.__tablename__ == "audit_logs"
    assert AuditLogModelDirect.__tablename__ == "audit_logs"


def test_audit_logs_migration_file_exists() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    migration = backend_root / "alembic" / "versions" / "h7d8e9f0a1b2_create_audit_logs_table.py"
    assert migration.is_file()
    content = migration.read_text(encoding="utf-8")
    assert 'revision: str = "h7d8e9f0a1b2"' in content
    assert "audit_logs" in content

"""Migration script safety checks for email verification."""

from pathlib import Path


def test_email_verification_migration_backfills_existing_users() -> None:
    migration = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "o4p5q6r7s8t0_email_verification_tokens.py"
    )
    text = migration.read_text(encoding="utf-8")
    assert "email_verification_tokens" in text
    assert "email_verified_at" in text
    assert "UPDATE users" in text
    assert "is_verified = TRUE" in text

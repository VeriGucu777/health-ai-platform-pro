"""Audit metadata sanitization — PHI must never enter audit_logs.metadata."""

from __future__ import annotations

import json
from typing import Any

from app.core.exceptions import ValidationError

METADATA_MAX_BYTES = 2048
METADATA_MAX_STRING_LENGTH = 256
METADATA_MAX_DEPTH = 1

ALLOWED_METADATA_KEYS = frozenset(
    {
        "risk_kind",
        "report",
        "format",
        "page",
        "page_size",
        "date_from",
        "date_to",
        "include_risk_snapshot",
        "reason_code",
        "is_primary",
        "consent_type",
        "status",
        "version",
        "child_kind",
        "child_id",
        "analytics_endpoint",
        "period",
        "assessment_type",
        "summary_version",
        "retrieval_version",
        "top_k",
        "source_types",
        "narrative_version",
        "prompt_version",
        "evidence_count",
        "provider_kind",
        "model_identifier",
        "fallback_used",
        "language",
        "max_evidence",
    }
)

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "email",
        "password",
        "hashed_password",
        "first_name",
        "last_name",
        "full_name",
        "name",
        "phone",
        "notes",
        "body",
        "request",
        "response",
        "payload",
        "token",
        "access_token",
        "refresh_token",
        "score",
        "probability",
        "timeline",
        "pdf",
        "content",
        "text",
        "diagnosis",
        "measurement",
        "blood_glucose",
        "systolic_pressure",
        "diastolic_pressure",
        "heart_rate",
    }
)


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


def _validate_value(value: Any, *, depth: int) -> Any:
    if depth > METADATA_MAX_DEPTH:
        raise ValidationError("Audit metadata nesting is too deep")

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if len(value) > METADATA_MAX_STRING_LENGTH:
            raise ValidationError("Audit metadata string value is too long")
        return value

    raise ValidationError("Audit metadata values must be string, int, bool, or null")


def sanitize_audit_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return sanitized metadata or None. Rejects PHI, bodies, and unknown keys."""
    if metadata is None:
        return None
    if not isinstance(metadata, dict):
        raise ValidationError("Audit metadata must be an object")

    sanitized: dict[str, Any] = {}
    for raw_key, raw_value in metadata.items():
        if not isinstance(raw_key, str):
            raise ValidationError("Audit metadata keys must be strings")

        normalized = _normalize_key(raw_key)
        if normalized in FORBIDDEN_METADATA_KEYS:
            raise ValidationError(f"Audit metadata key is not allowed: {raw_key}")
        if normalized not in ALLOWED_METADATA_KEYS:
            raise ValidationError(f"Audit metadata key is not allowed: {raw_key}")

        sanitized[normalized] = _validate_value(raw_value, depth=0)

    encoded = json.dumps(sanitized, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(encoded) > METADATA_MAX_BYTES:
        raise ValidationError("Audit metadata exceeds size limit")

    return sanitized

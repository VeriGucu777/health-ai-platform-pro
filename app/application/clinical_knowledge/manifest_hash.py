"""Deterministic manifest hashing for production rule sets."""

from __future__ import annotations

import hashlib
import json

from app.domain.clinical_knowledge.models import ClinicalRule

EMPTY_PRODUCTION_MANIFEST_PAYLOAD = "approved_prod_rules:v1:empty"


def rule_set_manifest_hash(rules: tuple[ClinicalRule, ...]) -> str:
    """SHA-256 identity for a production rule set (cross-platform, order-independent)."""
    if not rules:
        return hashlib.sha256(EMPTY_PRODUCTION_MANIFEST_PAYLOAD.encode("utf-8")).hexdigest()
    canonical = [
        {
            "rule_id": rule.rule_id,
            "rule_version": rule.rule_version,
            "source_refs": sorted(rule.source_refs),
        }
        for rule in sorted(rules, key=lambda r: r.rule_id)
    ]
    payload = "approved_prod_rules:v1:" + json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

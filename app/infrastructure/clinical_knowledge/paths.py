"""Safe path resolution for clinical knowledge catalogs."""

from pathlib import Path

_SOURCE_ID_ALLOWED = frozenset("abcdefghijklmnopqrstuvwxyz0123456789:_-")


def repository_clinical_knowledge_root() -> Path:
    """Default knowledge root at repository `clinical_knowledge/`."""
    return Path(__file__).resolve().parents[3] / "clinical_knowledge"


def assert_safe_source_id(source_id: str) -> None:
    """Reject identifiers that could be used for path traversal."""
    if not source_id or source_id != source_id.strip():
        raise ValueError("source_id must be non-empty and trimmed")
    lowered = source_id.lower()
    if ".." in lowered or "/" in source_id or "\\" in source_id:
        raise ValueError(f"unsafe source_id: {source_id!r}")
    if any(ch not in _SOURCE_ID_ALLOWED for ch in lowered):
        raise ValueError(f"source_id contains disallowed characters: {source_id!r}")


def assert_safe_rule_id(rule_id: str) -> None:
    if not rule_id or rule_id != rule_id.strip():
        raise ValueError("rule_id must be non-empty and trimmed")
    if ".." in rule_id or "/" in rule_id or "\\" in rule_id:
        raise ValueError(f"unsafe rule_id: {rule_id!r}")

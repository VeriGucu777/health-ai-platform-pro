"""Filter internal operational markers from user-visible clinical copy."""

from __future__ import annotations

# Shared with PDF report filtering — seed/idempotency markers must stay in DB only.
INTERNAL_OPERATIONAL_NOTE_PREFIXES: tuple[str, ...] = (
    "seed:",
    "demo-fixture:",
    "internal-test:",
)


def is_internal_operational_note(text: str | None) -> bool:
    if text is None:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    return any(lowered.startswith(prefix) for prefix in INTERNAL_OPERATIONAL_NOTE_PREFIXES)


def text_for_clinical_display(text: str | None) -> str | None:
    """Return text for timeline/summary UI, or None when value is an internal marker only."""
    if is_internal_operational_note(text):
        return None
    if text is None:
        return None
    stripped = text.strip()
    return stripped or None

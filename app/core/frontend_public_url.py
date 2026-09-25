"""FRONTEND_PUBLIC_URL validation for verification links."""

from __future__ import annotations

from urllib.parse import urlparse

from app.core.config import Settings


def validate_and_normalize_frontend_public_url(settings: Settings) -> Settings:
    """Ensure FRONTEND_PUBLIC_URL is valid; require HTTPS in production."""
    raw = (settings.frontend_public_url or "").strip()
    if not raw:
        msg = "FRONTEND_PUBLIC_URL must not be empty"
        raise ValueError(msg)

    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        msg = "FRONTEND_PUBLIC_URL must be a valid absolute http(s) URL"
        raise ValueError(msg)

    if settings.is_production and parsed.scheme != "https":
        msg = "FRONTEND_PUBLIC_URL must use https:// in production"
        raise ValueError(msg)

    normalized = raw.rstrip("/")
    if normalized != settings.frontend_public_url:
        return settings.model_copy(update={"frontend_public_url": normalized})
    return settings

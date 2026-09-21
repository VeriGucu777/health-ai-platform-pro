"""Per-user rate limiting for clinical narrative generation."""

from __future__ import annotations

from fastapi import Request

from app.api.deps import ClinicalUser
from app.core.exceptions import RateLimitExceededError
from app.core.logging import get_security_audit_logger
from app.middleware.auth_rate_limit import AuthRateLimiter

_audit_logger = get_security_audit_logger()


async def enforce_clinical_narrative_rate_limit(
    request: Request,
    current_user: ClinicalUser,
) -> None:
    settings = request.app.state.settings
    if not settings.clinical_narrative_rate_limit_enabled:
        return
    limiter: AuthRateLimiter = request.app.state.auth_rate_limiter
    try:
        limiter.check(
            scope="clinical_narrative",
            client_key=str(current_user.id),
            max_requests=settings.clinical_narrative_rate_limit,
            window_seconds=settings.clinical_narrative_rate_window_seconds,
        )
    except RateLimitExceededError:
        _audit_logger.warning(
            "Clinical narrative rate limit exceeded user_id=%s request_id=%s",
            current_user.id,
            getattr(request.state, "request_id", None),
        )
        raise

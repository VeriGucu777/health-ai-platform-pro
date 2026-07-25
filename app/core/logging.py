"""Structured logging configuration."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.core.log_redaction import SensitiveDataFilter
from app.core.request_context import get_correlation_id, get_request_id


class RequestContextFilter(logging.Filter):
    """Attach request identifiers from context vars to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = get_request_id()
        if request_id is not None:
            record.request_id = request_id
        correlation_id = get_correlation_id()
        if correlation_id is not None:
            record.correlation_id = correlation_id
        return True


class JsonLogFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "correlation_id", "method", "path_template", "status_code"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging(settings: Settings | None = None) -> None:
    """Configure root logger with redaction and optional JSON output."""
    settings = settings or get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if settings.log_format == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ),
        )
    handler.addFilter(SensitiveDataFilter())
    handler.addFilter(RequestContextFilter())

    logging.basicConfig(level=log_level, handlers=[handler], force=True)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for module-level use."""
    return logging.getLogger(name)


def get_security_audit_logger() -> logging.Logger:
    """Return the dedicated security audit logger."""
    return logging.getLogger("security.audit")

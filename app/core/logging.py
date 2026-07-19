"""Structured logging configuration."""

import logging
import sys

from app.core.config import Settings, get_settings


def setup_logging(settings: Settings | None = None) -> None:
    """Configure root logger with a consistent format."""
    settings = settings or get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for module-level use."""
    return logging.getLogger(name)

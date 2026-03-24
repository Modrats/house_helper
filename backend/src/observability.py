"""Observability utilities — structured logging.

Thin wrapper around the standard library so callers don't import
logging directly. Swap the implementation here to integrate a
structured-logging library (e.g. structlog) in the future.
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a standard Python logger for the given module name."""
    return logging.getLogger(name)

"""Reusable exception types for the house_helper backend."""


class MissingConfigError(Exception):
    """Raised when required configuration (e.g. environment variables) is absent."""

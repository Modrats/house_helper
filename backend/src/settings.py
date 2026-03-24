"""Application settings loaded from environment variables.

All settings are read from environment variables — no hardcoded defaults.
Missing required variables raise KeyError loudly at startup so
misconfiguration is caught immediately (per team convention).
"""

from __future__ import annotations

import os


class Settings:
    """Application settings sourced exclusively from environment variables.

    Per team convention: no fallback defaults — every variable must be
    explicitly set so misconfiguration fails loudly at runtime.
    """

    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins for the API.

        Read from the CORS_ORIGINS environment variable as a
        comma-separated list of origin URLs.

        Example::

            CORS_ORIGINS=http://localhost:5173,https://app.example.com
        """
        raw = os.environ["CORS_ORIGINS"]
        return [o.strip() for o in raw.split(",") if o.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

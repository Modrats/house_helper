"""Application settings — environment-driven configuration via Pydantic Settings.

Handles all environment-level config: paths, API keys, server params, observability.
Pipeline-specific criteria remain in config/criteria.yaml (loaded by config.py).

Usage:
    from src.settings import get_settings
    settings = get_settings()
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Two levels up from src/settings.py → backend/, then one more → repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Central application settings, loaded from environment variables and .env file.

    Secrets (API keys) have no defaults and will be None until set.
    Services that require them should check at initialization and raise early.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Storage paths (defaults resolve relative to repo root) ---
    input_data_path: Path = Field(
        default=_REPO_ROOT / "input_data",
        description="Base path to input data directory.",
    )
    output_path: Path = Field(
        default=_REPO_ROOT / "outputs",
        description="Base path to output directory.",
    )

    # --- Azure OpenAI ---
    azure_openai_endpoint: str | None = Field(
        default=None,
        description="Azure OpenAI service endpoint URL.",
    )
    azure_openai_api_key: str | None = Field(
        default=None,
        description="Azure OpenAI API key. Required when using LLM services.",
    )
    azure_openai_deployment: str | None = Field(
        default=None,
        description="Azure OpenAI model deployment name.",
    )

    # --- FLUX (imagineering) ---
    flux_api_key: str | None = Field(
        default=None,
        description="API key for FLUX.2-pro image generation. Required for imagineering.",
    )
    flux_api_url: str | None = Field(
        default=None,
        description="FLUX API base URL.",
    )

    # --- Distance calculator ---
    distance_api_key: str | None = Field(
        default=None,
        description="API key for distance calculation service.",
    )

    # --- FastAPI server ---
    api_host: str = Field(
        default="0.0.0.0",
        description="Host address for the FastAPI server.",
    )
    api_port: int = Field(
        default=8000,
        description="Port for the FastAPI server.",
    )

    # --- Observability ---
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )

    # --- CORS ---
    cors_origins: list[str] = Field(
        default=["http://localhost:5173"],
        description="Allowed CORS origins for the frontend.",
    )

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, v: str) -> str:
        """Uppercase and validate the log level string."""
        v = v.upper()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v not in valid:
            msg = f"Invalid log_level '{v}'. Must be one of {sorted(valid)}."
            raise ValueError(msg)
        return v

    def require_azure_openai(self) -> None:
        """Assert that Azure OpenAI credentials are configured.

        Raises:
            RuntimeError: If any required Azure OpenAI setting is missing.
        """
        missing = [
            name
            for name in ("azure_openai_endpoint", "azure_openai_api_key", "azure_openai_deployment")
            if getattr(self, name) is None
        ]
        if missing:
            raise RuntimeError(
                f"Missing required Azure OpenAI settings: {', '.join(missing)}. "
                "Set them via environment variables or .env file."
            )

    def require_flux(self) -> None:
        """Assert that FLUX credentials are configured.

        Raises:
            RuntimeError: If any required FLUX setting is missing.
        """
        missing = [name for name in ("flux_api_key", "flux_api_url") if getattr(self, name) is None]
        if missing:
            raise RuntimeError(
                f"Missing required FLUX settings: {', '.join(missing)}. "
                "Set them via environment variables or .env file."
            )

    def require_distance(self) -> None:
        """Assert that the distance API key is configured.

        Raises:
            RuntimeError: If the distance API key is missing.
        """
        if self.distance_api_key is None:
            raise RuntimeError(
                "Missing required setting: distance_api_key. "
                "Set it via environment variable or .env file."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance.

    The first call loads from environment / .env file.
    Subsequent calls return the same object.

    Returns:
        The application Settings.
    """
    return Settings()

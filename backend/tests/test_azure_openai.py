"""Unit tests for AzureOpenAIService — config loading and construction."""

from __future__ import annotations

import os
from typing import NamedTuple
from unittest.mock import patch

import pytest

from src.exceptions import MissingConfigError
from src.services.azure_openai_service import load_azure_openai_config

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------


class MissingEnvVarCase(NamedTuple):
    """Test case for missing Azure OpenAI env vars."""

    description: str
    env_vars: dict[str, str]
    expected_missing: str


MISSING_ENV_VAR_CASES = [
    MissingEnvVarCase(
        description="missing AZURE_OPENAI_ENDPOINT raises MissingConfigError",
        env_vars={
            "AZURE_OPENAI_API_KEY": "key-123",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
        },
        expected_missing="AZURE_OPENAI_ENDPOINT",
    ),
    MissingEnvVarCase(
        description="missing AZURE_OPENAI_API_KEY raises MissingConfigError",
        env_vars={
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
        },
        expected_missing="AZURE_OPENAI_API_KEY",
    ),
    MissingEnvVarCase(
        description="missing AZURE_OPENAI_DEPLOYMENT raises MissingConfigError",
        env_vars={
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "key-123",
        },
        expected_missing="AZURE_OPENAI_DEPLOYMENT",
    ),
    MissingEnvVarCase(
        description="all missing raises MissingConfigError listing all vars",
        env_vars={},
        expected_missing="AZURE_OPENAI_ENDPOINT",
    ),
]


class WhitespaceEnvVarCase(NamedTuple):
    """Test case for whitespace-only env var values."""

    description: str
    env_vars: dict[str, str]
    expected_missing: str


WHITESPACE_ENV_VAR_CASES = [
    WhitespaceEnvVarCase(
        description="whitespace-only AZURE_OPENAI_ENDPOINT is accepted (not stripped)",
        env_vars={
            "AZURE_OPENAI_ENDPOINT": "   ",
            "AZURE_OPENAI_API_KEY": "key-123",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
        },
        expected_missing="AZURE_OPENAI_ENDPOINT",
    ),
    WhitespaceEnvVarCase(
        description="whitespace-only AZURE_OPENAI_API_KEY is accepted (not stripped)",
        env_vars={
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "  \t  ",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
        },
        expected_missing="AZURE_OPENAI_API_KEY",
    ),
]


# ===========================================================================
# Happy path
# ===========================================================================

# --- load_azure_openai_config ---


def test_load_config_all_set_returns_dict() -> None:
    """load_azure_openai_config returns dict when all vars are set."""
    # Arrange
    env = {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "key-12345",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
    }

    # Act
    with patch.dict(os.environ, env, clear=False):
        config = load_azure_openai_config()

    # Assert
    assert config["AZURE_OPENAI_ENDPOINT"] == "https://test.openai.azure.com"
    assert config["AZURE_OPENAI_API_KEY"] == "key-12345"
    assert config["AZURE_OPENAI_DEPLOYMENT"] == "gpt-4o"


# ===========================================================================
# Edge cases
# ===========================================================================

# --- load_azure_openai_config ---


@pytest.mark.parametrize(
    "description, env_vars, expected_missing",
    WHITESPACE_ENV_VAR_CASES,
    ids=[c.description for c in WHITESPACE_ENV_VAR_CASES],
)
def test_load_config_whitespace_only_accepted(
    description: str, env_vars: dict[str, str], expected_missing: str
) -> None:
    """Whitespace-only values are accepted — source does not strip."""
    # Arrange
    cleared = {
        "AZURE_OPENAI_ENDPOINT": "",
        "AZURE_OPENAI_API_KEY": "",
        "AZURE_OPENAI_DEPLOYMENT": "",
    }
    cleared.update(env_vars)

    # Act
    with patch.dict(os.environ, cleared, clear=False):
        config = load_azure_openai_config()

    # Assert — whitespace value passes through (not stripped)
    assert config[expected_missing].strip() == ""


def test_load_config_returns_all_expected_keys() -> None:
    """Config dict contains all three expected keys."""
    # Arrange
    env = {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "key-12345",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
    }

    # Act
    with patch.dict(os.environ, env, clear=False):
        config = load_azure_openai_config()

    # Assert
    expected_keys = {"AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"}
    assert set(config.keys()) == expected_keys


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- load_azure_openai_config ---


@pytest.mark.parametrize(
    "description, env_vars, expected_missing",
    MISSING_ENV_VAR_CASES,
    ids=[c.description for c in MISSING_ENV_VAR_CASES],
)
def test_load_config_missing_env_raises(
    description: str, env_vars: dict[str, str], expected_missing: str
) -> None:
    """load_azure_openai_config raises MissingConfigError for missing env vars."""
    # Arrange
    cleared = {
        "AZURE_OPENAI_ENDPOINT": "",
        "AZURE_OPENAI_API_KEY": "",
        "AZURE_OPENAI_DEPLOYMENT": "",
    }
    cleared.update(env_vars)

    # Act & Assert
    with patch.dict(os.environ, cleared, clear=False):
        with pytest.raises(MissingConfigError, match=expected_missing):
            load_azure_openai_config()


def test_load_config_empty_string_treated_as_missing() -> None:
    """Empty string values are treated as missing config."""
    # Arrange
    env = {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
    }

    # Act & Assert
    with patch.dict(os.environ, env, clear=False):
        with pytest.raises(MissingConfigError, match="AZURE_OPENAI_API_KEY"):
            load_azure_openai_config()

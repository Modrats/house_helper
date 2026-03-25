"""Unit tests for core.py — composition root factory functions."""

from __future__ import annotations

import os
from typing import NamedTuple
from unittest.mock import patch

import pytest

from src.services.house_repository import HouseRepository
from src.services.local_storage import LocalStorage

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------


class ImagineeringMissingEnvCase(NamedTuple):
    """Test case for missing env vars in create_imagineering_service."""

    description: str
    env_vars: dict[str, str]
    expected_missing: str


IMAGINEERING_MISSING_ENV_CASES = [
    ImagineeringMissingEnvCase(
        description="missing FLUX_API_KEY raises RuntimeError",
        env_vars={"FLUX_ENDPOINT": "https://flux.test", "FLUX_GUIDANCE": "15.0"},
        expected_missing="FLUX_API_KEY",
    ),
    ImagineeringMissingEnvCase(
        description="missing FLUX_ENDPOINT raises RuntimeError",
        env_vars={"FLUX_API_KEY": "key-123", "FLUX_GUIDANCE": "15.0"},
        expected_missing="FLUX_ENDPOINT",
    ),
    ImagineeringMissingEnvCase(
        description="missing FLUX_GUIDANCE raises RuntimeError",
        env_vars={"FLUX_API_KEY": "key-123", "FLUX_ENDPOINT": "https://flux.test"},
        expected_missing="FLUX_GUIDANCE",
    ),
]


# ===========================================================================
# Happy path
# ===========================================================================

# --- create_storage ---


def test_create_storage_returns_local_storage() -> None:
    """create_storage returns a LocalStorage instance."""
    # Arrange — (no setup needed)

    # Act
    from src.core import create_storage

    result = create_storage()

    # Assert
    assert isinstance(result, LocalStorage)


# --- create_repository ---


def test_create_repository_returns_house_repository() -> None:
    """create_repository returns a HouseRepository wired to local storage."""
    # Arrange — (no setup needed)

    # Act
    from src.core import create_repository

    repo = create_repository()

    # Assert
    assert isinstance(repo, HouseRepository)


# --- create_room_classifier ---


def test_create_room_classifier_reads_env_vars() -> None:
    """create_room_classifier uses env vars and returns a classifier."""
    # Arrange
    env = {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "test-key-12345",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
        "ROOM_CLASSIFIER_BATCH_SIZE": "3",
    }

    # Act
    with patch.dict(os.environ, env, clear=False):
        from src.core import create_room_classifier

        classifier = create_room_classifier()

    # Assert
    assert classifier is not None
    assert classifier._batch_size == 3


# --- create_imagineering_service ---


def test_create_imagineering_service_with_all_env_vars() -> None:
    """create_imagineering_service succeeds when all required env vars are set."""
    # Arrange
    env = {
        "FLUX_API_KEY": "test-key",
        "FLUX_ENDPOINT": "https://flux.example.com/generate",
        "FLUX_GUIDANCE": "15.0",
    }

    # Act
    with patch.dict(os.environ, env, clear=False):
        from src.core import create_imagineering_service

        service = create_imagineering_service()

    # Assert
    assert service is not None


def test_create_imagineering_service_with_seed() -> None:
    """create_imagineering_service passes optional FLUX_SEED."""
    # Arrange
    env = {
        "FLUX_API_KEY": "test-key",
        "FLUX_ENDPOINT": "https://flux.example.com/generate",
        "FLUX_GUIDANCE": "15.0",
        "FLUX_SEED": "42",
    }

    # Act
    with patch.dict(os.environ, env, clear=False):
        from src.core import create_imagineering_service

        service = create_imagineering_service()

    # Assert
    assert service._default_seed == 42


# ===========================================================================
# Edge cases
# ===========================================================================

# --- create_room_classifier ---


def test_create_room_classifier_default_batch_size() -> None:
    """create_room_classifier uses default batch size of 5 when env var is unset."""
    # Arrange
    env = {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "test-key-12345",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
    }
    cleared = {"ROOM_CLASSIFIER_BATCH_SIZE": ""}

    # Act
    with patch.dict(os.environ, {**env, **cleared}, clear=False):
        os.environ.pop("ROOM_CLASSIFIER_BATCH_SIZE", None)
        from src.core import create_room_classifier

        classifier = create_room_classifier()

    # Assert
    assert classifier._batch_size == 5


# --- create_imagineering_service ---


def test_create_imagineering_service_no_seed_defaults_to_none() -> None:
    """create_imagineering_service sets default_seed to None when FLUX_SEED is unset."""
    # Arrange
    env = {
        "FLUX_API_KEY": "test-key",
        "FLUX_ENDPOINT": "https://flux.example.com/generate",
        "FLUX_GUIDANCE": "15.0",
    }

    # Act
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("FLUX_SEED", None)
        from src.core import create_imagineering_service

        service = create_imagineering_service()

    # Assert
    assert service._default_seed is None


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- create_imagineering_service ---


@pytest.mark.parametrize(
    "description, env_vars, expected_missing",
    IMAGINEERING_MISSING_ENV_CASES,
    ids=[c.description for c in IMAGINEERING_MISSING_ENV_CASES],
)
def test_create_imagineering_service_missing_env(
    description: str, env_vars: dict[str, str], expected_missing: str
) -> None:
    """create_imagineering_service raises RuntimeError for missing env vars."""
    # Arrange
    cleared = {k: "" for k in ("FLUX_API_KEY", "FLUX_ENDPOINT", "FLUX_GUIDANCE", "FLUX_SEED")}
    cleared.update(env_vars)

    # Act & Assert
    with patch.dict(os.environ, cleared, clear=False):
        from src.core import create_imagineering_service

        with pytest.raises(RuntimeError, match=expected_missing):
            create_imagineering_service()


# --- create_llm_text_filter ---


def test_create_llm_text_filter_requires_azure_config() -> None:
    """create_llm_text_filter requires Azure OpenAI env vars."""
    # Arrange
    cleared = {
        k: "" for k in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
    }

    # Act & Assert
    with patch.dict(os.environ, cleared, clear=False):
        from src.core import create_llm_text_filter
        from src.exceptions import MissingConfigError

        with pytest.raises(MissingConfigError):
            create_llm_text_filter()

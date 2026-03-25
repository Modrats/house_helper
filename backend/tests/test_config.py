"""Unit tests for config.py — ConfigLoader YAML config loading."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import pytest
import yaml

from src.config import ConfigLoader

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------


class CriteriaCase(NamedTuple):
    """Test case for ConfigLoader.criteria()."""

    description: str
    yaml_data: dict
    expected_keys: list[str]
    excluded_keys: list[str]


CRITERIA_CASES = [
    CriteriaCase(
        description="merges filter sections and excludes storage",
        yaml_data={
            "storage": {"input_dir": "input_data", "output_dir": "outputs"},
            "text_filter": {"p1_keywords": ["garden"], "p2_keywords": ["garage"]},
        },
        expected_keys=["p1_keywords", "p2_keywords"],
        excluded_keys=["input_dir", "output_dir"],
    ),
    CriteriaCase(
        description="multiple filter sections are merged into flat dict",
        yaml_data={
            "storage": {"input_dir": "in", "output_dir": "out"},
            "text_filter": {"p1_keywords": ["garden"]},
            "llm_text_filter": {"p1_criteria": ["has a garden"]},
        },
        expected_keys=["p1_keywords", "p1_criteria"],
        excluded_keys=["input_dir"],
    ),
    CriteriaCase(
        description="non-dict sections are skipped gracefully",
        yaml_data={
            "storage": {"input_dir": "in", "output_dir": "out"},
            "text_filter": {"p1_keywords": ["garden"]},
            "version": "1.0",
        },
        expected_keys=["p1_keywords"],
        excluded_keys=["version"],
    ),
]


class EdgeCriteriaCase(NamedTuple):
    """Test case for ConfigLoader.criteria() edge cases."""

    description: str
    yaml_content: str
    expected_result: dict


EDGE_CRITERIA_CASES = [
    EdgeCriteriaCase(
        description="YAML with only storage section returns empty criteria",
        yaml_content=yaml.dump({"storage": {"input_dir": "in", "output_dir": "out"}}),
        expected_result={},
    ),
    EdgeCriteriaCase(
        description="config with empty filter section dict returns empty criteria",
        yaml_content=yaml.dump(
            {
                "storage": {"input_dir": "in", "output_dir": "out"},
                "text_filter": {},
            }
        ),
        expected_result={},
    ),
]


# ===========================================================================
# Happy path
# ===========================================================================

# --- _load (internal YAML parse) ---


def test_load_parses_yaml(tmp_path: Path) -> None:
    """ConfigLoader._load() reads and parses a YAML file."""
    # Arrange
    config_path = tmp_path / "test.yaml"
    config_path.write_text(yaml.dump({"key": "value", "nested": {"a": 1}}))

    # Act
    loader = ConfigLoader(config_path)
    result = loader._load()

    # Assert
    assert result["key"] == "value"
    assert result["nested"]["a"] == 1


def test_load_caches_result(tmp_path: Path) -> None:
    """ConfigLoader._load() reads the file once and caches subsequent calls."""
    # Arrange
    config_path = tmp_path / "test.yaml"
    config_path.write_text(yaml.dump({"key": "original"}))
    loader = ConfigLoader(config_path)

    # Act
    first = loader._load()
    config_path.write_text(yaml.dump({"key": "changed"}))
    second = loader._load()

    # Assert
    assert first is second
    assert first["key"] == "original"


# --- criteria ---


@pytest.mark.parametrize(
    "description, yaml_data, expected_keys, excluded_keys",
    CRITERIA_CASES,
    ids=[c.description for c in CRITERIA_CASES],
)
def test_criteria(
    tmp_path: Path,
    description: str,
    yaml_data: dict,
    expected_keys: list[str],
    excluded_keys: list[str],
) -> None:
    """ConfigLoader.criteria() merges filter sections and excludes storage."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text(yaml.dump(yaml_data))

    # Act
    result = ConfigLoader(config_path).criteria()

    # Assert
    for key in expected_keys:
        assert key in result, f"Expected key '{key}' not found"
    for key in excluded_keys:
        assert key not in result, f"Excluded key '{key}' should not appear"


# --- storage_paths ---


def test_storage_paths_returns_absolute_paths(tmp_path: Path) -> None:
    """ConfigLoader.storage_paths() returns absolute paths."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text(
        yaml.dump(
            {
                "storage": {"input_dir": "input_data/houses", "output_dir": "outputs/houses"},
            }
        )
    )

    # Act
    input_dir, output_dir = ConfigLoader(config_path).storage_paths()

    # Assert
    assert input_dir.is_absolute()
    assert output_dir.is_absolute()
    assert str(input_dir).endswith("input_data/houses")
    assert str(output_dir).endswith("outputs/houses")


# --- distance_config ---


def test_distance_config_returns_destinations(tmp_path: Path) -> None:
    """ConfigLoader.distance_config() returns the destinations list."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text(
        yaml.dump(
            {
                "storage": {"input_dir": "in", "output_dir": "out"},
                "distance": {
                    "destinations": [
                        {"label": "Work", "addresses": ["123 Main St"]},
                    ]
                },
            }
        )
    )

    # Act
    result = ConfigLoader(config_path).distance_config()

    # Assert
    assert len(result) == 1
    assert result[0]["label"] == "Work"


# --- photo_criteria ---


def test_photo_criteria_returns_room_criteria(tmp_path: Path) -> None:
    """ConfigLoader.photo_criteria() returns criteria keyed by room type."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text(
        yaml.dump(
            {
                "storage": {"input_dir": "in", "output_dir": "out"},
                "photo_criteria": {
                    "kitchen": {"must_have": ["sink", "stove"]},
                },
            }
        )
    )

    # Act
    result = ConfigLoader(config_path).photo_criteria()

    # Assert
    assert "kitchen" in result
    assert result["kitchen"]["must_have"] == ["sink", "stove"]


# ===========================================================================
# Edge cases
# ===========================================================================

# --- criteria ---


@pytest.mark.parametrize(
    "description, yaml_content, expected_result",
    EDGE_CRITERIA_CASES,
    ids=[c.description for c in EDGE_CRITERIA_CASES],
)
def test_criteria_edge_cases(
    tmp_path: Path,
    description: str,
    yaml_content: str,
    expected_result: dict,
) -> None:
    """ConfigLoader.criteria() handles edge-case YAML inputs gracefully."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text(yaml_content)

    # Act
    result = ConfigLoader(config_path).criteria()

    # Assert
    assert result == expected_result


def test_default_path_used_when_none_provided() -> None:
    """ConfigLoader uses default YAML path when no path provided."""
    # Arrange — (no setup needed)

    # Act
    loader = ConfigLoader()

    # Assert
    assert loader._path.name == "criteria.yaml"
    assert loader._path.is_absolute()


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- criteria ---


def test_criteria_empty_yaml_raises(tmp_path: Path) -> None:
    """ConfigLoader.criteria() raises AttributeError when YAML is empty (parses as None)."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text("")

    # Act & Assert
    with pytest.raises(AttributeError):
        ConfigLoader(config_path).criteria()


# --- storage_paths ---


def test_storage_paths_missing_section_raises(tmp_path: Path) -> None:
    """ConfigLoader.storage_paths() raises KeyError when storage section is missing."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text(yaml.dump({"text_filter": {"p1": ["garden"]}}))

    # Act & Assert
    with pytest.raises(KeyError):
        ConfigLoader(config_path).storage_paths()


# --- file not found ---


def test_loader_raises_on_missing_file(tmp_path: Path) -> None:
    """ConfigLoader raises FileNotFoundError when YAML file does not exist."""
    # Arrange
    config_path = tmp_path / "nonexistent.yaml"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        ConfigLoader(config_path).criteria()

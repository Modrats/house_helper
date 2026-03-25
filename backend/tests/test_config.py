"""Unit tests for config.py — YAML config loading."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import pytest
import yaml

from src.config import _load_raw, load_criteria, load_storage_paths

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------


class LoadCriteriaCase(NamedTuple):
    """Test case for load_criteria."""

    description: str
    yaml_data: dict
    expected_keys: list[str]
    excluded_keys: list[str]


LOAD_CRITERIA_CASES = [
    LoadCriteriaCase(
        description="merges filter sections and excludes storage",
        yaml_data={
            "storage": {"input_dir": "input_data", "output_dir": "outputs"},
            "text_filter": {"p1_keywords": ["garden"], "p2_keywords": ["garage"]},
        },
        expected_keys=["p1_keywords", "p2_keywords"],
        excluded_keys=["input_dir", "output_dir"],
    ),
    LoadCriteriaCase(
        description="multiple filter sections are merged into flat dict",
        yaml_data={
            "storage": {"input_dir": "in", "output_dir": "out"},
            "text_filter": {"p1_keywords": ["garden"]},
            "llm_text_filter": {"p1_criteria": ["has a garden"]},
        },
        expected_keys=["p1_keywords", "p1_criteria"],
        excluded_keys=["input_dir"],
    ),
    LoadCriteriaCase(
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
    """Test case for load_criteria edge cases."""

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

# --- _load_raw ---


def test_load_raw_parses_yaml(tmp_path: Path) -> None:
    """_load_raw reads and parses a YAML file."""
    # Arrange
    config_path = tmp_path / "test.yaml"
    config_path.write_text(yaml.dump({"key": "value", "nested": {"a": 1}}))

    # Act
    result = _load_raw(config_path)

    # Assert
    assert result["key"] == "value"
    assert result["nested"]["a"] == 1


# --- load_criteria ---


@pytest.mark.parametrize(
    "description, yaml_data, expected_keys, excluded_keys",
    LOAD_CRITERIA_CASES,
    ids=[c.description for c in LOAD_CRITERIA_CASES],
)
def test_load_criteria(
    tmp_path: Path,
    description: str,
    yaml_data: dict,
    expected_keys: list[str],
    excluded_keys: list[str],
) -> None:
    """load_criteria merges filter sections and excludes storage."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text(yaml.dump(yaml_data))

    # Act
    result = load_criteria(config_path)

    # Assert
    for key in expected_keys:
        assert key in result, f"Expected key '{key}' not found"
    for key in excluded_keys:
        assert key not in result, f"Excluded key '{key}' should not appear"


# --- load_storage_paths ---


def test_load_storage_paths_returns_absolute_paths(tmp_path: Path) -> None:
    """load_storage_paths returns absolute paths relative to repo root."""
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
    input_dir, output_dir = load_storage_paths(config_path)

    # Assert
    assert input_dir.is_absolute()
    assert output_dir.is_absolute()
    assert str(input_dir).endswith("input_data/houses")
    assert str(output_dir).endswith("outputs/houses")


# ===========================================================================
# Edge cases
# ===========================================================================

# --- load_criteria ---


@pytest.mark.parametrize(
    "description, yaml_content, expected_result",
    EDGE_CRITERIA_CASES,
    ids=[c.description for c in EDGE_CRITERIA_CASES],
)
def test_load_criteria_edge_cases(
    tmp_path: Path,
    description: str,
    yaml_content: str,
    expected_result: dict,
) -> None:
    """load_criteria handles edge-case YAML inputs gracefully."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text(yaml_content)

    # Act
    result = load_criteria(config_path)

    # Assert
    assert result == expected_result


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- load_criteria ---


def test_load_criteria_empty_yaml_raises(tmp_path: Path) -> None:
    """load_criteria raises AttributeError when YAML file is empty (parses as None)."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text("")

    # Act & Assert
    with pytest.raises(AttributeError):
        load_criteria(config_path)


# --- load_storage_paths ---


def test_load_storage_paths_missing_section_raises(tmp_path: Path) -> None:
    """load_storage_paths raises KeyError when storage section is missing."""
    # Arrange
    config_path = tmp_path / "criteria.yaml"
    config_path.write_text(yaml.dump({"text_filter": {"p1": ["garden"]}}))

    # Act & Assert
    with pytest.raises(KeyError):
        load_storage_paths(config_path)

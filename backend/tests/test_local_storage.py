"""Unit tests for LocalStorage — filesystem-backed IDataSource."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

import pytest

from src.services.local_storage import LocalStorage

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------


class JsonRoundtripCase(NamedTuple):
    """Test case for JSON read/write round-trip."""

    description: str
    data: dict


JSON_ROUNDTRIP_CASES = [
    JsonRoundtripCase(
        description="simple flat dict survives write then read",
        data={"name": "test_house", "price": 350000},
    ),
    JsonRoundtripCase(
        description="nested dict with lists survives round-trip",
        data={"rooms": ["kitchen", "bedroom"], "meta": {"area_m2": 120}},
    ),
    JsonRoundtripCase(
        description="empty dict survives round-trip",
        data={},
    ),
]


class ListKeysCase(NamedTuple):
    """Test case for list_keys."""

    description: str
    files_to_create: list[str]
    expected_count: int


LIST_KEYS_CASES = [
    ListKeysCase(
        description="existing directory with files returns all entries sorted",
        files_to_create=["b.txt", "a.txt", "c.txt"],
        expected_count=3,
    ),
    ListKeysCase(
        description="empty directory returns empty list",
        files_to_create=[],
        expected_count=0,
    ),
]


class ExistsCase(NamedTuple):
    """Test case for exists."""

    description: str
    create_file: bool
    expected: bool


EXISTS_CASES = [
    ExistsCase(
        description="existing file returns True",
        create_file=True,
        expected=True,
    ),
    ExistsCase(
        description="non-existent path returns False",
        create_file=False,
        expected=False,
    ),
]


# ===========================================================================
# Happy path
# ===========================================================================

# --- read_json / write_json ---


@pytest.mark.parametrize(
    "description, data",
    JSON_ROUNDTRIP_CASES,
    ids=[c.description for c in JSON_ROUNDTRIP_CASES],
)
def test_json_roundtrip(tmp_path: Path, description: str, data: dict) -> None:
    """write_json then read_json returns identical data."""
    # Arrange
    storage = LocalStorage()
    path = tmp_path / "data.json"

    # Act
    storage.write_json(path, data)
    result = storage.read_json(path)

    # Assert
    assert result == data


def test_write_json_creates_parent_directories(tmp_path: Path) -> None:
    """write_json creates intermediate directories if they don't exist."""
    # Arrange
    storage = LocalStorage()
    path = tmp_path / "deep" / "nested" / "dir" / "file.json"

    # Act
    storage.write_json(path, {"ok": True})

    # Assert
    assert path.exists()
    assert storage.read_json(path) == {"ok": True}


def test_write_json_appends_trailing_newline(tmp_path: Path) -> None:
    """JSON output ends with a newline for POSIX compliance."""
    # Arrange
    storage = LocalStorage()
    path = tmp_path / "data.json"

    # Act
    storage.write_json(path, {"key": "value"})

    # Assert
    raw = path.read_text(encoding="utf-8")
    assert raw.endswith("\n")


# --- list_keys ---


@pytest.mark.parametrize(
    "description, files_to_create, expected_count",
    LIST_KEYS_CASES,
    ids=[c.description for c in LIST_KEYS_CASES],
)
def test_list_keys(
    tmp_path: Path, description: str, files_to_create: list[str], expected_count: int
) -> None:
    """list_keys returns sorted entries for existing directories."""
    # Arrange
    storage = LocalStorage()
    for fname in files_to_create:
        (tmp_path / fname).write_text("content")

    # Act
    result = storage.list_keys(tmp_path)

    # Assert
    assert len(result) == expected_count
    assert result == sorted(result)


# --- read_bytes ---


def test_read_bytes_returns_file_content(tmp_path: Path) -> None:
    """read_bytes returns raw bytes from a file."""
    # Arrange
    storage = LocalStorage()
    path = tmp_path / "photo.jpg"
    content = b"\x89PNG fake image data"
    path.write_bytes(content)

    # Act
    result = storage.read_bytes(path)

    # Assert
    assert result == content


# --- exists ---


@pytest.mark.parametrize(
    "description, create_file, expected",
    EXISTS_CASES,
    ids=[c.description for c in EXISTS_CASES],
)
def test_exists(tmp_path: Path, description: str, create_file: bool, expected: bool) -> None:
    """exists returns correct boolean for present/absent paths."""
    # Arrange
    storage = LocalStorage()
    path = tmp_path / "test_file.txt"
    if create_file:
        path.write_text("content")

    # Act
    result = storage.exists(path)

    # Assert
    assert result is expected


# ===========================================================================
# Edge cases
# ===========================================================================

# --- list_keys ---


def test_list_keys_missing_directory(tmp_path: Path) -> None:
    """list_keys returns empty list for non-existent directory."""
    # Arrange
    storage = LocalStorage()

    # Act
    result = storage.list_keys(tmp_path / "nonexistent")

    # Assert
    assert result == []


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- read_json ---


def test_read_json_nonexistent_file_raises(tmp_path: Path) -> None:
    """read_json raises FileNotFoundError on nonexistent file."""
    # Arrange
    storage = LocalStorage()
    path = tmp_path / "missing.json"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        storage.read_json(path)


def test_read_json_malformed_json_raises(tmp_path: Path) -> None:
    """read_json raises JSONDecodeError on malformed JSON content."""
    # Arrange
    storage = LocalStorage()
    path = tmp_path / "bad.json"
    path.write_text("{not valid json{{", encoding="utf-8")

    # Act & Assert
    with pytest.raises(json.JSONDecodeError):
        storage.read_json(path)


# --- read_bytes ---


def test_read_bytes_nonexistent_file_raises(tmp_path: Path) -> None:
    """read_bytes raises FileNotFoundError on nonexistent file."""
    # Arrange
    storage = LocalStorage()
    path = tmp_path / "missing.bin"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        storage.read_bytes(path)

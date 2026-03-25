"""Unit tests for AzureOpenAIRoomClassifier service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple
from unittest.mock import MagicMock

import pytest

from src.models.classification import HouseClassifications, PhotoClassification
from src.models.room import RoomType
from src.services.room_classifier import AzureOpenAIRoomClassifier, _media_type_for

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------


def _make_classifier(
    tmp_path: Path,
    llm_service: MagicMock | None = None,
    batch_size: int = 5,
) -> AzureOpenAIRoomClassifier:
    """Create a classifier with a tmp_path-based directory structure."""
    service = llm_service or MagicMock()
    return AzureOpenAIRoomClassifier(
        llm_service=service,
        input_dir=tmp_path / "input",
        output_dir=tmp_path / "output",
        batch_size=batch_size,
    )


def _create_photo(tmp_path: Path, slug: str, filename: str) -> Path:
    """Create a minimal photo file under the expected directory structure."""
    photo_dir = tmp_path / "input" / "houses" / slug / "photos"
    photo_dir.mkdir(parents=True, exist_ok=True)
    photo_path = photo_dir / filename
    photo_path.write_bytes(b"\x89PNG minimal image data")
    return photo_path


class DiscoverPhotosCase(NamedTuple):
    """Test case for _discover_photos."""

    description: str
    files: list[str]
    expected_count: int


DISCOVER_PHOTOS_CASES = [
    DiscoverPhotosCase(
        description="finds supported image files",
        files=["kitchen.jpg", "bath.png", "yard.webp"],
        expected_count=3,
    ),
    DiscoverPhotosCase(
        description="ignores non-image files",
        files=["kitchen.jpg", "notes.txt", "plan.pdf"],
        expected_count=1,
    ),
    DiscoverPhotosCase(
        description="empty directory returns empty list",
        files=[],
        expected_count=0,
    ),
]


class LoadPreviousCase(NamedTuple):
    """Test case for _load_previous_results."""

    description: str
    file_content: str | None
    expected_count: int


LOAD_PREVIOUS_CASES = [
    LoadPreviousCase(
        description="valid JSON with classifications returns PhotoClassification list",
        file_content=json.dumps(
            {
                "slug": "test_house",
                "classifications": [
                    {"filename": "k.jpg", "room_type": "kitchen", "confidence": 0.9},
                    {"filename": "b.jpg", "room_type": "bedroom", "confidence": 0.85},
                ],
            }
        ),
        expected_count=2,
    ),
    LoadPreviousCase(
        description="corrupt JSON returns empty list",
        file_content="not valid json {{{",
        expected_count=0,
    ),
    LoadPreviousCase(
        description="file does not exist returns empty list",
        file_content=None,
        expected_count=0,
    ),
    LoadPreviousCase(
        description="JSON with missing classification keys returns empty list",
        file_content=json.dumps(
            {
                "slug": "test_house",
                "classifications": [
                    {"filename": "k.jpg"},
                ],
            }
        ),
        expected_count=0,
    ),
]


class MediaTypeCase(NamedTuple):
    """Test case for _media_type_for."""

    description: str
    suffix: str
    expected: str


MEDIA_TYPE_CASES = [
    MediaTypeCase(description="jpg maps to image/jpeg", suffix=".jpg", expected="image/jpeg"),
    MediaTypeCase(description="jpeg maps to image/jpeg", suffix=".jpeg", expected="image/jpeg"),
    MediaTypeCase(description="png maps to image/png", suffix=".png", expected="image/png"),
    MediaTypeCase(description="webp maps to image/webp", suffix=".webp", expected="image/webp"),
    MediaTypeCase(description="gif maps to image/gif", suffix=".gif", expected="image/gif"),
    MediaTypeCase(
        description="unknown extension defaults to image/jpeg",
        suffix=".bmp",
        expected="image/jpeg",
    ),
]


# ===========================================================================
# Happy path
# ===========================================================================

# --- _discover_photos ---


@pytest.mark.parametrize(
    "description, files, expected_count",
    DISCOVER_PHOTOS_CASES,
    ids=[c.description for c in DISCOVER_PHOTOS_CASES],
)
def test_discover_photos(
    tmp_path: Path, description: str, files: list[str], expected_count: int
) -> None:
    """_discover_photos finds only supported image files."""
    # Arrange
    classifier = _make_classifier(tmp_path)
    slug = "test_house"
    photo_dir = tmp_path / "input" / "houses" / slug / "photos"
    photo_dir.mkdir(parents=True, exist_ok=True)
    for fname in files:
        (photo_dir / fname).write_bytes(b"data")

    # Act
    result = classifier._discover_photos(slug)

    # Assert
    assert len(result) == expected_count


# --- _load_previous_results ---


@pytest.mark.parametrize(
    "description, file_content, expected_count",
    LOAD_PREVIOUS_CASES,
    ids=[c.description for c in LOAD_PREVIOUS_CASES],
)
def test_load_previous_results(
    tmp_path: Path, description: str, file_content: str | None, expected_count: int
) -> None:
    """_load_previous_results handles valid, corrupt, and missing files."""
    # Arrange
    output_file = tmp_path / "classifications.json"
    if file_content is not None:
        output_file.write_text(file_content, encoding="utf-8")

    # Act
    result = AzureOpenAIRoomClassifier._load_previous_results(output_file)

    # Assert
    assert len(result) == expected_count


# --- _save_results ---


def test_save_results_writes_json(tmp_path: Path) -> None:
    """_save_results writes classifications as formatted JSON with trailing newline."""
    # Arrange
    output_file = tmp_path / "output" / "room_classifications.json"
    classifications = HouseClassifications(
        slug="test_house",
        classifications=[
            PhotoClassification(filename="k.jpg", room_type=RoomType.KITCHEN, confidence=0.9),
        ],
    )

    # Act
    AzureOpenAIRoomClassifier._save_results(output_file, classifications)

    # Assert
    assert output_file.exists()
    raw = output_file.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    data = json.loads(raw)
    assert data["slug"] == "test_house"
    assert len(data["classifications"]) == 1


def test_save_results_creates_parent_dirs(tmp_path: Path) -> None:
    """_save_results creates parent directories if they don't exist."""
    # Arrange
    output_file = tmp_path / "deep" / "nested" / "classifications.json"
    classifications = HouseClassifications(slug="test_house")

    # Act
    AzureOpenAIRoomClassifier._save_results(output_file, classifications)

    # Assert
    assert output_file.exists()


# --- _classify_batch ---


def test_classify_batch_calls_llm_and_returns_classifications(tmp_path: Path) -> None:
    """_classify_batch sends photos to LLM and returns classifications."""
    # Arrange
    mock_llm = MagicMock()

    class FakeItem:
        label = "image_1"
        room_type = RoomType.KITCHEN
        confidence = 0.92
        description = "Modern kitchen"
        group_id = 1

    class FakeResult:
        results = [FakeItem()]

    mock_llm.classify_image.return_value = FakeResult()
    classifier = _make_classifier(tmp_path, llm_service=mock_llm)
    photo = _create_photo(tmp_path, "test_house", "kitchen.jpg")

    # Act
    result = classifier._classify_batch([photo])

    # Assert
    assert len(result) == 1
    assert result[0].filename == "kitchen.jpg"
    assert result[0].room_type == RoomType.KITCHEN


# --- classify_house (idempotent) ---


def test_classify_house_skips_already_classified(tmp_path: Path) -> None:
    """classify_house skips photos that were classified in a previous run."""
    # Arrange
    mock_llm = MagicMock()
    classifier = _make_classifier(tmp_path, llm_service=mock_llm)
    _create_photo(tmp_path, "test_house", "kitchen.jpg")
    output_file = tmp_path / "output" / "houses" / "test_house" / "room_classifications.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(
            {
                "slug": "test_house",
                "classifications": [
                    {"filename": "kitchen.jpg", "room_type": "kitchen", "confidence": 0.9}
                ],
            }
        )
    )

    # Act
    result = classifier.classify_house("test_house")

    # Assert
    assert len(result.classifications) == 1
    mock_llm.classify_image.assert_not_called()


# --- _media_type_for ---


@pytest.mark.parametrize(
    "description, suffix, expected",
    MEDIA_TYPE_CASES,
    ids=[c.description for c in MEDIA_TYPE_CASES],
)
def test_media_type_for(description: str, suffix: str, expected: str) -> None:
    """_media_type_for maps file extensions to correct MIME types."""
    # Arrange — (no setup needed)

    # Act
    result = _media_type_for(suffix)

    # Assert
    assert result == expected


# ===========================================================================
# Edge cases
# ===========================================================================

# --- _discover_photos ---


def test_discover_photos_no_photos_dir(tmp_path: Path) -> None:
    """_discover_photos returns empty list when photos directory doesn't exist."""
    # Arrange
    classifier = _make_classifier(tmp_path)

    # Act
    result = classifier._discover_photos("nonexistent_house")

    # Assert
    assert result == []


# --- classify_house ---


def test_classify_house_no_photos_returns_empty(tmp_path: Path) -> None:
    """classify_house returns empty result when no photos exist."""
    # Arrange
    classifier = _make_classifier(tmp_path)

    # Act
    result = classifier.classify_house("nonexistent")

    # Assert
    assert result.slug == "nonexistent"
    assert result.classifications == []


# --- _classify_batch ---


def test_classify_batch_empty_response_skips(tmp_path: Path) -> None:
    """_classify_batch skips photos that get no LLM results."""
    # Arrange
    mock_llm = MagicMock()

    class EmptyResult:
        results = []

    mock_llm.classify_image.return_value = EmptyResult()
    classifier = _make_classifier(tmp_path, llm_service=mock_llm)
    photo = _create_photo(tmp_path, "test_house", "mystery.jpg")

    # Act
    result = classifier._classify_batch([photo])

    # Assert
    assert result == []


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- classify_house with invalid room type in LLM response ---


def test_classify_batch_invalid_room_type(tmp_path: Path) -> None:
    """_classify_batch handles invalid room type from LLM by using the raw value."""
    # Arrange
    mock_llm = MagicMock()

    class FakeItem:
        label = "image_1"
        room_type = "unknown"
        confidence = 0.5
        description = "Can't determine"
        group_id = 1

    class FakeResult:
        results = [FakeItem()]

    mock_llm.classify_image.return_value = FakeResult()
    classifier = _make_classifier(tmp_path, llm_service=mock_llm)
    photo = _create_photo(tmp_path, "test_house", "weird.jpg")

    # Act
    result = classifier._classify_batch([photo])

    # Assert
    assert len(result) == 1
    assert result[0].room_type == RoomType.UNKNOWN


# --- classify_house on nonexistent house slug ---


def test_classify_house_nonexistent_slug_returns_empty(tmp_path: Path) -> None:
    """classify_house on nonexistent house slug returns empty classifications."""
    # Arrange
    classifier = _make_classifier(tmp_path)

    # Act
    result = classifier.classify_house("does-not-exist")

    # Assert
    assert result.slug == "does-not-exist"
    assert result.classifications == []

"""Unit tests for HouseRepository — domain layer wrapping IDataSource."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

import pytest

from src.interfaces.data_source import IDataSource
from src.models.house import FilterResult, HouseStatus
from src.services.house_repository import HouseRepository

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------


class FakeStorage(IDataSource):
    """In-memory storage for testing HouseRepository without touching the filesystem."""

    def __init__(self) -> None:
        self._json: dict[str, dict] = {}
        self._bytes: dict[str, bytes] = {}
        self._dirs: dict[str, list[str]] = {}

    def seed_listing(self, base: Path, slug: str, text: str) -> None:
        """Create a minimal house with a listing.txt."""
        listing_path = str(base / slug / "listing.txt")
        self._bytes[listing_path] = text.encode("utf-8")
        parent = str(base)
        self._dirs.setdefault(parent, [])
        child = str(base / slug)
        if child not in self._dirs[parent]:
            self._dirs[parent].append(child)

    def seed_photo(self, base: Path, slug: str, filename: str, data: bytes = b"img") -> None:
        """Add a photo file to a house."""
        photos_dir = base / slug / "photos"
        photo_path = str(photos_dir / filename)
        self._bytes[photo_path] = data
        key = str(photos_dir)
        self._dirs.setdefault(key, [])
        if photo_path not in self._dirs[key]:
            self._dirs[key].append(photo_path)

    def seed_json(self, path: Path, data: dict) -> None:
        """Seed a JSON file at the given path."""
        self._json[str(path)] = data

    def read_json(self, path: str | Path) -> dict:
        key = str(path)
        if key not in self._json:
            raise FileNotFoundError(key)
        return self._json[key]

    def write_json(self, path: str | Path, data: dict) -> None:
        self._json[str(path)] = data

    def list_keys(self, prefix: str | Path) -> list[str]:
        return sorted(self._dirs.get(str(prefix), []))

    def read_bytes(self, path: str | Path) -> bytes:
        key = str(path)
        if key not in self._bytes:
            raise FileNotFoundError(key)
        return self._bytes[key]

    def exists(self, path: str | Path) -> bool:
        key = str(path)
        return key in self._json or key in self._bytes or key in self._dirs


INPUT = Path("/data/input")
OUTPUT = Path("/data/output")


def _make_repo(storage: FakeStorage | None = None) -> tuple[FakeStorage, HouseRepository]:
    """Create a FakeStorage + HouseRepository pair."""
    s = storage or FakeStorage()
    return s, HouseRepository(s, INPUT, OUTPUT)


# ===========================================================================
# Happy path
# ===========================================================================

# --- list_houses ---


def test_list_houses_returns_slugs_with_listings() -> None:
    """list_houses returns sorted slugs that have a listing.txt."""
    # Arrange
    storage, repo = _make_repo()
    storage.seed_listing(INPUT, "beta_house", "Nice beta house")
    storage.seed_listing(INPUT, "alpha_house", "Nice alpha house")

    # Act
    result = repo.list_houses()

    # Assert
    assert result == ["alpha_house", "beta_house"]


# --- load_houses ---


def test_load_houses_creates_house_objects() -> None:
    """load_houses produces House objects from listings."""
    # Arrange
    storage, repo = _make_repo()
    storage.seed_listing(INPUT, "test_house", "Beautiful 3-bedroom home with garden")

    # Act
    houses = repo.load_houses(criteria={})

    # Assert
    assert len(houses) == 1
    assert houses[0].slug == "test_house"
    assert houses[0].listing_text == "Beautiful 3-bedroom home with garden"
    assert houses[0].status == HouseStatus.RAW


def test_load_houses_restores_filter_state() -> None:
    """load_houses restores status and filter results from prior output."""
    # Arrange
    storage, repo = _make_repo()
    storage.seed_listing(INPUT, "test_house", "Has a garden")
    filter_output = OUTPUT / "test_house" / "criteria" / "filter_result.json"
    saved = {
        "slug": "test_house",
        "status": "filtered",
        "filter_results": {
            "p1": {"garden": True},
            "p2": {},
            "excluded": {},
        },
    }
    storage.seed_json(filter_output, saved)
    criteria = {"p1_keywords": ["garden"], "p2_keywords": [], "excluded_keywords": []}

    # Act
    houses = repo.load_houses(criteria=criteria)

    # Assert
    assert houses[0].status == HouseStatus.FILTERED
    assert houses[0].filter_results.p1 == {"garden": True}


# --- save_filter_results ---


def test_save_filter_results_writes_json() -> None:
    """save_filter_results persists filter results for each house."""
    # Arrange
    storage, repo = _make_repo()
    storage.seed_listing(INPUT, "test_house", "Test listing")
    houses = repo.load_houses(criteria={})
    house = houses[0].with_filter_result(FilterResult(p1={"garden": True}))
    house = house.with_status(HouseStatus.FILTERED)

    # Act
    repo.save_filter_results([house])

    # Assert
    expected_path = str(OUTPUT / "test_house" / "criteria" / "filter_result.json")
    assert expected_path in storage._json
    saved = storage._json[expected_path]
    assert saved["slug"] == "test_house"
    assert saved["status"] == "filtered"


# --- get_house ---


def test_get_house_returns_full_house() -> None:
    """get_house returns a House with listing text, photos, and status."""
    # Arrange
    storage, repo = _make_repo()
    storage.seed_listing(INPUT, "test_house", "Beautiful home")
    storage.seed_photo(INPUT, "test_house", "kitchen.jpg")
    storage.seed_photo(INPUT, "test_house", "garden.png")
    storage._bytes[str(INPUT / "test_house" / "photos")] = b""

    # Act
    house = repo.get_house("test_house")

    # Assert
    assert house.slug == "test_house"
    assert house.listing_text == "Beautiful home"
    assert len(house.photos) == 2


def test_get_house_restores_filter_state_from_output() -> None:
    """get_house loads filter results from output if available."""
    # Arrange
    storage, repo = _make_repo()
    storage.seed_listing(INPUT, "test_house", "Nice home")
    filter_output = OUTPUT / "test_house" / "criteria" / "filter_result.json"
    storage.seed_json(
        filter_output,
        {
            "status": "filtered",
            "filter_results": {"p1": {"garden": True}, "p2": {}, "excluded": {}},
        },
    )

    # Act
    house = repo.get_house("test_house")

    # Assert
    assert house.status == HouseStatus.FILTERED
    assert house.filter_results.p1 == {"garden": True}


# --- get_photos ---


def test_get_photos_returns_image_paths() -> None:
    """get_photos returns paths for image files only."""
    # Arrange
    storage, repo = _make_repo()
    storage.seed_listing(INPUT, "test_house", "Home")
    storage._bytes[str(INPUT / "test_house")] = b""
    storage.seed_photo(INPUT, "test_house", "living.jpg")
    storage.seed_photo(INPUT, "test_house", "plan.pdf", b"pdf")

    # Act
    photos = repo.get_photos("test_house")

    # Assert
    assert any("living.jpg" in p for p in photos)
    assert not any("plan.pdf" in p for p in photos)


# --- get_room_classifications ---


def test_get_room_classifications_returns_mappings() -> None:
    """get_room_classifications returns room-to-photo mappings."""
    # Arrange
    storage, repo = _make_repo()
    classifications = {"kitchen": ["k1.jpg", "k2.jpg"], "bedroom": ["b1.jpg"]}
    storage.seed_json(OUTPUT / "test_house" / "classifications.json", classifications)

    # Act
    result = repo.get_room_classifications("test_house")

    # Assert
    assert result == classifications


# --- get_criteria_results ---


def test_get_criteria_results_returns_filter_result() -> None:
    """get_criteria_results reads and returns FilterResult from output."""
    # Arrange
    storage, repo = _make_repo()
    storage.seed_json(
        OUTPUT / "test_house" / "criteria" / "filter_result.json",
        {"filter_results": {"p1": {"garden": True}, "p2": {"garage": False}, "excluded": {}}},
    )

    # Act
    result = repo.get_criteria_results("test_house")

    # Assert
    assert result.p1 == {"garden": True}
    assert result.p2 == {"garage": False}


# --- get_imagineered_photos ---


def test_get_imagineered_photos_returns_image_paths() -> None:
    """get_imagineered_photos returns paths for imagineered image files."""
    # Arrange
    storage, repo = _make_repo()
    img_dir = str(OUTPUT / "test_house" / "imagineered")
    storage._dirs[img_dir] = [
        f"{img_dir}/living.jpg",
        f"{img_dir}/notes.txt",
    ]

    # Act
    result = repo.get_imagineered_photos("test_house")

    # Assert
    assert len(result) == 1
    assert "living.jpg" in result[0]


# --- get_photo_bytes ---


def test_get_photo_bytes_returns_raw_bytes() -> None:
    """get_photo_bytes returns raw file content."""
    # Arrange
    storage, repo = _make_repo()
    photo_data = b"\x89PNG fake photo"
    storage._bytes[str(INPUT / "test_house" / "photos" / "img.jpg")] = photo_data

    # Act
    result = repo.get_photo_bytes("test_house", "img.jpg")

    # Assert
    assert result == photo_data


# --- get_imagineered_photo_bytes ---


def test_get_imagineered_photo_bytes_returns_raw_bytes() -> None:
    """get_imagineered_photo_bytes returns raw file content."""
    # Arrange
    storage, repo = _make_repo()
    data = b"\x89PNG imagineered"
    storage._bytes[str(OUTPUT / "test_house" / "imagineered" / "img.jpg")] = data

    # Act
    result = repo.get_imagineered_photo_bytes("test_house", "img.jpg")

    # Assert
    assert result == data


# ===========================================================================
# Edge cases
# ===========================================================================

# --- list_houses ---


def test_list_houses_skips_dirs_without_listing() -> None:
    """list_houses ignores directories that have no listing.txt."""
    # Arrange
    storage, repo = _make_repo()
    storage.seed_listing(INPUT, "good_house", "Has listing")
    storage._dirs.setdefault(str(INPUT), []).append(str(INPUT / "empty_house"))

    # Act
    result = repo.list_houses()

    # Assert
    assert result == ["good_house"]


# --- load_houses ---


def test_load_houses_resets_on_criteria_drift() -> None:
    """load_houses resets status to RAW when criteria have changed."""
    # Arrange
    storage, repo = _make_repo()
    storage.seed_listing(INPUT, "test_house", "Has a garden")
    filter_output = OUTPUT / "test_house" / "criteria" / "filter_result.json"
    saved = {
        "status": "filtered",
        "filter_results": {
            "p1": {"garden": True},
            "p2": {},
            "excluded": {},
        },
    }
    storage.seed_json(filter_output, saved)
    criteria = {"p1_keywords": ["pool"], "p2_keywords": [], "excluded_keywords": []}

    # Act
    houses = repo.load_houses(criteria=criteria)

    # Assert
    assert houses[0].status == HouseStatus.RAW
    assert houses[0].filter_results == FilterResult()


# --- get_room_classifications ---


def test_get_room_classifications_missing_returns_empty() -> None:
    """get_room_classifications returns empty dict when file doesn't exist."""
    # Arrange
    _, repo = _make_repo()

    # Act
    result = repo.get_room_classifications("nonexistent")

    # Assert
    assert result == {}


# --- get_criteria_results ---


def test_get_criteria_results_missing_returns_empty_filter_result() -> None:
    """get_criteria_results returns empty FilterResult when output doesn't exist."""
    # Arrange
    _, repo = _make_repo()

    # Act
    result = repo.get_criteria_results("nonexistent")

    # Assert
    assert result == FilterResult()


# --- get_imagineered_photos ---


def test_get_imagineered_photos_empty_returns_empty() -> None:
    """get_imagineered_photos returns empty list when no files exist."""
    # Arrange
    _, repo = _make_repo()

    # Act
    result = repo.get_imagineered_photos("nonexistent")

    # Assert
    assert result == []


# --- _criteria_match ---


class CriteriaMatchCase(NamedTuple):
    """Test case for criteria drift detection."""

    description: str
    saved: dict[str, Any]
    current: dict[str, Any]
    expected: bool


CRITERIA_MATCH_CASES = [
    CriteriaMatchCase(
        description="identical criteria match",
        saved={
            "filter_results": {
                "p1": {"garden": True},
                "p2": {"garage": False},
                "excluded": {"highway": False},
            }
        },
        current={
            "p1_keywords": ["garden"],
            "p2_keywords": ["garage"],
            "excluded_keywords": ["highway"],
        },
        expected=True,
    ),
    CriteriaMatchCase(
        description="added p1 keyword causes mismatch",
        saved={"filter_results": {"p1": {"garden": True}, "p2": {}, "excluded": {}}},
        current={"p1_keywords": ["garden", "pool"], "p2_keywords": [], "excluded_keywords": []},
        expected=False,
    ),
    CriteriaMatchCase(
        description="removed p2 keyword causes mismatch",
        saved={
            "filter_results": {
                "p1": {},
                "p2": {"garage": True, "dishwasher": False},
                "excluded": {},
            }
        },
        current={"p1_keywords": [], "p2_keywords": ["garage"], "excluded_keywords": []},
        expected=False,
    ),
    CriteriaMatchCase(
        description="empty saved and empty current match",
        saved={"filter_results": {"p1": {}, "p2": {}, "excluded": {}}},
        current={"p1_keywords": [], "p2_keywords": [], "excluded_keywords": []},
        expected=True,
    ),
    CriteriaMatchCase(
        description="missing filter_results key in saved still matches empty current",
        saved={},
        current={"p1_keywords": [], "p2_keywords": [], "excluded_keywords": []},
        expected=True,
    ),
]


@pytest.mark.parametrize(
    "description, saved, current, expected",
    CRITERIA_MATCH_CASES,
    ids=[c.description for c in CRITERIA_MATCH_CASES],
)
def test_criteria_match(description: str, saved: dict, current: dict, expected: bool) -> None:
    """_criteria_match detects criteria drift correctly."""
    # Arrange — (no setup needed, data from parametrize)

    # Act
    result = HouseRepository._criteria_match(saved, current)

    # Assert
    assert result is expected


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- get_house ---


def test_get_house_not_found_raises() -> None:
    """get_house raises FileNotFoundError for unknown slugs."""
    # Arrange
    _, repo = _make_repo()

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="not found"):
        repo.get_house("nonexistent")


# --- get_photos ---


def test_get_photos_not_found_raises() -> None:
    """get_photos raises FileNotFoundError for unknown houses."""
    # Arrange
    _, repo = _make_repo()

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="not found"):
        repo.get_photos("nonexistent")


# --- get_photo_bytes ---


def test_get_photo_bytes_not_found_raises() -> None:
    """get_photo_bytes raises FileNotFoundError for missing photos."""
    # Arrange
    _, repo = _make_repo()

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="not found"):
        repo.get_photo_bytes("test_house", "missing.jpg")


# --- get_imagineered_photo_bytes ---


def test_get_imagineered_photo_bytes_not_found_raises() -> None:
    """get_imagineered_photo_bytes raises FileNotFoundError for missing files."""
    # Arrange
    _, repo = _make_repo()

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="not found"):
        repo.get_imagineered_photo_bytes("test_house", "missing.jpg")

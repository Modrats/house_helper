"""Unit tests for the photo criteria checker service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple
from unittest.mock import MagicMock

import pytest

from src.config import load_photo_criteria
from src.interfaces.llm_service import ILLMService
from src.models.house import FilterResult
from src.models.llm import LLMResponse
from src.models.photo_criteria import (
    FeatureCheck,
    PhotoCriteriaResult,
    RoomCriteriaResult,
)
from src.models.room import RoomType
from src.services.photo_checker import (
    VisionPhotoChecker,
    _FeatureEval,
    _PhotoCheckResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CRITERIA: dict[str, dict[str, list[str]]] = {
    "kitchen": {
        "required": ["dishwasher", "oven", "sink"],
        "preferred": ["island", "modern_cabinets"],
    },
    "bedroom": {
        "required": ["bed"],
        "preferred": ["built_in_wardrobe", "natural_light"],
    },
    "living_room": {
        "required": [],
        "preferred": ["fireplace", "natural_light"],
    },
}


def _make_classifications_json(
    slug: str,
    entries: list[dict],
) -> dict:
    """Build a room_classifications.json payload."""
    return {"slug": slug, "classifications": entries}


def _setup_house(
    tmp_path: Path,
    slug: str,
    photo_names: list[str],
    classifications: list[dict] | None = None,
) -> tuple[Path, Path]:
    """Create input photos and optional classification output for a house.

    Returns (input_dir, output_dir).
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    photos_dir = input_dir / "houses" / slug / "photos"
    photos_dir.mkdir(parents=True)
    for name in photo_names:
        (photos_dir / name).write_bytes(b"\x89PNG fake image data")

    if classifications is not None:
        cls_dir = output_dir / slug
        cls_dir.mkdir(parents=True)
        cls_file = cls_dir / "room_classifications.json"
        cls_file.write_text(
            json.dumps(
                _make_classifications_json(slug, classifications),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return input_dir, output_dir


def _mock_llm_response(features: list[dict]) -> _PhotoCheckResult:
    """Build a _PhotoCheckResult from simple feature dicts."""
    return _PhotoCheckResult(
        features=[
            _FeatureEval(
                feature_name=f["feature_name"],
                present=f["present"],
                confidence=f["confidence"],
                notes=f.get("notes", ""),
            )
            for f in features
        ]
    )


# ---------------------------------------------------------------------------
# FeatureCheck model
# ---------------------------------------------------------------------------


class FeatureCheckCase(NamedTuple):
    """Test case for FeatureCheck model creation and immutability."""

    description: str
    feature_name: str
    present: bool
    confidence: float
    notes: str


FEATURE_CHECK_CASES = [
    FeatureCheckCase(
        description="present feature with high confidence",
        feature_name="dishwasher",
        present=True,
        confidence=0.95,
        notes="Clearly visible under the counter",
    ),
    FeatureCheckCase(
        description="absent feature with zero confidence",
        feature_name="heated_floor",
        present=False,
        confidence=0.0,
        notes="No evidence of underfloor heating",
    ),
    FeatureCheckCase(
        description="boundary confidence value of 1.0",
        feature_name="sink",
        present=True,
        confidence=1.0,
        notes="Kitchen sink fully visible",
    ),
]


@pytest.mark.parametrize(
    "description, feature_name, present, confidence, notes",
    FEATURE_CHECK_CASES,
)
def test_feature_check_creation(
    description: str,
    feature_name: str,
    present: bool,
    confidence: float,
    notes: str,
) -> None:
    check = FeatureCheck(
        feature_name=feature_name,
        present=present,
        confidence=confidence,
        notes=notes,
    )
    assert check.feature_name == feature_name
    assert check.present == present
    assert check.confidence == confidence
    assert check.notes == notes


def test_feature_check_frozen() -> None:
    check = FeatureCheck(feature_name="bed", present=True, confidence=0.9, notes="yes")
    with pytest.raises(Exception):
        check.feature_name = "sofa"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RoomCriteriaResult — meets_required / meets_preferred
# ---------------------------------------------------------------------------


class MeetsRequiredCase(NamedTuple):
    """Test case for RoomCriteriaResult.meets_required computed field."""

    description: str
    required_present: list[bool]
    expected: bool


MEETS_REQUIRED_CASES = [
    MeetsRequiredCase(
        description="all required present → meets_required is True",
        required_present=[True, True, True],
        expected=True,
    ),
    MeetsRequiredCase(
        description="one required missing → meets_required is False",
        required_present=[True, False, True],
        expected=False,
    ),
    MeetsRequiredCase(
        description="no required features → meets_required is True (vacuous)",
        required_present=[],
        expected=True,
    ),
]


@pytest.mark.parametrize(
    "description, required_present, expected",
    MEETS_REQUIRED_CASES,
)
def test_meets_required(description: str, required_present: list[bool], expected: bool) -> None:
    checks = [
        FeatureCheck(
            feature_name=f"feat_{i}",
            present=p,
            confidence=0.9,
            notes="",
        )
        for i, p in enumerate(required_present)
    ]
    result = RoomCriteriaResult(
        room_type=RoomType.KITCHEN,
        photo_filename="photo.jpg",
        required_features=checks,
    )
    assert result.meets_required == expected


class MeetsPreferredCase(NamedTuple):
    """Test case for RoomCriteriaResult.meets_preferred computed field."""

    description: str
    preferred_present: list[bool]
    expected: bool


MEETS_PREFERRED_CASES = [
    MeetsPreferredCase(
        description="at least one preferred present → True",
        preferred_present=[False, True],
        expected=True,
    ),
    MeetsPreferredCase(
        description="no preferred present → False",
        preferred_present=[False, False],
        expected=False,
    ),
    MeetsPreferredCase(
        description="no preferred features defined → True (vacuous)",
        preferred_present=[],
        expected=True,
    ),
]


@pytest.mark.parametrize(
    "description, preferred_present, expected",
    MEETS_PREFERRED_CASES,
)
def test_meets_preferred(description: str, preferred_present: list[bool], expected: bool) -> None:
    checks = [
        FeatureCheck(
            feature_name=f"feat_{i}",
            present=p,
            confidence=0.5,
            notes="",
        )
        for i, p in enumerate(preferred_present)
    ]
    result = RoomCriteriaResult(
        room_type=RoomType.BEDROOM,
        photo_filename="photo.jpg",
        preferred_features=checks,
    )
    assert result.meets_preferred == expected


# ---------------------------------------------------------------------------
# PhotoCriteriaResult — to_filter_result
# ---------------------------------------------------------------------------


class ToFilterResultCase(NamedTuple):
    """Test case for PhotoCriteriaResult.to_filter_result() conversion."""

    description: str
    room_results: list[RoomCriteriaResult]
    expected_p1: dict[str, bool]
    expected_p2: dict[str, bool]


TO_FILTER_RESULT_CASES = [
    ToFilterResultCase(
        description="single room with required and preferred features",
        room_results=[
            RoomCriteriaResult(
                room_type=RoomType.KITCHEN,
                photo_filename="kitchen.jpg",
                required_features=[
                    FeatureCheck(
                        feature_name="dishwasher",
                        present=True,
                        confidence=0.9,
                        notes="",
                    ),
                    FeatureCheck(
                        feature_name="oven",
                        present=False,
                        confidence=0.3,
                        notes="",
                    ),
                ],
                preferred_features=[
                    FeatureCheck(
                        feature_name="island",
                        present=True,
                        confidence=0.8,
                        notes="",
                    ),
                ],
            )
        ],
        expected_p1={"kitchen:dishwasher": True, "kitchen:oven": False},
        expected_p2={"kitchen:island": True},
    ),
    ToFilterResultCase(
        description="empty room results produce empty filter result",
        room_results=[],
        expected_p1={},
        expected_p2={},
    ),
]


@pytest.mark.parametrize(
    "description, room_results, expected_p1, expected_p2",
    TO_FILTER_RESULT_CASES,
)
def test_to_filter_result(
    description: str,
    room_results: list[RoomCriteriaResult],
    expected_p1: dict[str, bool],
    expected_p2: dict[str, bool],
) -> None:
    result = PhotoCriteriaResult(slug="test-house", room_results=room_results)
    fr = result.to_filter_result()
    assert isinstance(fr, FilterResult)
    assert fr.p1 == expected_p1
    assert fr.p2 == expected_p2


# ---------------------------------------------------------------------------
# PhotoCriteriaResult — to_detailed_dict
# ---------------------------------------------------------------------------


def test_to_detailed_dict_structure() -> None:
    result = PhotoCriteriaResult(
        slug="test-house",
        room_results=[
            RoomCriteriaResult(
                room_type=RoomType.BEDROOM,
                photo_filename="bed.jpg",
                required_features=[
                    FeatureCheck(
                        feature_name="bed",
                        present=True,
                        confidence=0.99,
                        notes="Large double bed",
                    )
                ],
                preferred_features=[],
            )
        ],
    )
    detailed = result.to_detailed_dict()
    assert len(detailed) == 1
    entry = detailed[0]
    assert entry["room_type"] == "bedroom"
    assert entry["photo_filename"] == "bed.jpg"
    assert entry["meets_required"] is True
    assert entry["meets_preferred"] is True
    assert len(entry["required_features"]) == 1
    assert entry["required_features"][0]["feature_name"] == "bed"


# ---------------------------------------------------------------------------
# Model serialization roundtrip
# ---------------------------------------------------------------------------


def test_photo_criteria_result_json_roundtrip() -> None:
    original = PhotoCriteriaResult(
        slug="test",
        room_results=[
            RoomCriteriaResult(
                room_type=RoomType.KITCHEN,
                photo_filename="k.jpg",
                required_features=[
                    FeatureCheck(
                        feature_name="sink",
                        present=True,
                        confidence=0.9,
                        notes="visible",
                    )
                ],
            )
        ],
    )
    data = json.loads(original.model_dump_json())
    restored = PhotoCriteriaResult.model_validate(data)
    assert restored.slug == original.slug
    assert len(restored.room_results) == 1
    assert restored.room_results[0].required_features[0].feature_name == "sink"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def test_load_photo_criteria_from_default_config() -> None:
    criteria = load_photo_criteria()
    assert "kitchen" in criteria
    assert "required" in criteria["kitchen"]
    assert "preferred" in criteria["kitchen"]
    assert "dishwasher" in criteria["kitchen"]["required"]


def test_load_photo_criteria_missing_section(tmp_path: Path) -> None:
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("storage:\n  input_dir: x\n  output_dir: y\n")
    with pytest.raises(KeyError):
        load_photo_criteria(config_file)


# ---------------------------------------------------------------------------
# VisionPhotoChecker — check_house integration
# ---------------------------------------------------------------------------


def test_check_house_basic(tmp_path: Path) -> None:
    """Full check_house with a mocked LLM returns expected results."""
    slug = "test-house"
    input_dir, output_dir = _setup_house(
        tmp_path,
        slug,
        photo_names=["kitchen.jpg"],
        classifications=[
            {
                "filename": "kitchen.jpg",
                "room_type": "kitchen",
                "confidence": 0.95,
            }
        ],
    )

    mock_llm = MagicMock(spec=ILLMService)
    mock_llm.classify_image.return_value = _mock_llm_response(
        [
            {"feature_name": "dishwasher", "present": True, "confidence": 0.9},
            {"feature_name": "oven", "present": True, "confidence": 0.85},
            {"feature_name": "sink", "present": True, "confidence": 0.95},
            {"feature_name": "island", "present": False, "confidence": 0.2},
            {
                "feature_name": "modern_cabinets",
                "present": True,
                "confidence": 0.7,
            },
        ]
    )

    checker = VisionPhotoChecker(
        llm_service=mock_llm,
        input_dir=input_dir,
        output_dir=output_dir,
        criteria=SAMPLE_CRITERIA,
    )
    result = checker.check_house(slug)

    assert result.slug == slug
    assert len(result.room_results) == 1

    room = result.room_results[0]
    assert room.room_type == RoomType.KITCHEN
    assert room.photo_filename == "kitchen.jpg"
    assert room.meets_required is True
    assert len(room.required_features) == 3
    assert len(room.preferred_features) == 2

    mock_llm.classify_image.assert_called_once()


# ---------------------------------------------------------------------------
# Idempotent re-runs
# ---------------------------------------------------------------------------


def test_check_house_idempotent(tmp_path: Path) -> None:
    """Second run with same classifications skips LLM calls."""
    slug = "test-house"
    input_dir, output_dir = _setup_house(
        tmp_path,
        slug,
        photo_names=["kitchen.jpg"],
        classifications=[
            {
                "filename": "kitchen.jpg",
                "room_type": "kitchen",
                "confidence": 0.95,
            }
        ],
    )

    mock_llm = MagicMock(spec=ILLMService)
    mock_llm.classify_image.return_value = _mock_llm_response(
        [
            {"feature_name": "dishwasher", "present": True, "confidence": 0.9},
            {"feature_name": "oven", "present": True, "confidence": 0.85},
            {"feature_name": "sink", "present": True, "confidence": 0.95},
            {"feature_name": "island", "present": False, "confidence": 0.2},
            {
                "feature_name": "modern_cabinets",
                "present": True,
                "confidence": 0.7,
            },
        ]
    )

    checker = VisionPhotoChecker(
        llm_service=mock_llm,
        input_dir=input_dir,
        output_dir=output_dir,
        criteria=SAMPLE_CRITERIA,
    )

    # First run — should call LLM
    result1 = checker.check_house(slug)
    assert mock_llm.classify_image.call_count == 1
    assert len(result1.room_results) == 1

    # Second run — should skip LLM
    result2 = checker.check_house(slug)
    assert mock_llm.classify_image.call_count == 1  # no additional calls
    assert len(result2.room_results) == 1


# ---------------------------------------------------------------------------
# Missing classifications
# ---------------------------------------------------------------------------


def test_check_house_no_classifications(tmp_path: Path) -> None:
    """check_house returns empty result when no classifications exist."""
    slug = "no-data"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    mock_llm = MagicMock(spec=ILLMService)
    checker = VisionPhotoChecker(
        llm_service=mock_llm,
        input_dir=input_dir,
        output_dir=output_dir,
        criteria=SAMPLE_CRITERIA,
    )

    result = checker.check_house(slug)
    assert result.slug == slug
    assert result.room_results == []
    mock_llm.classify_image.assert_not_called()


# ---------------------------------------------------------------------------
# Room type with no criteria configured
# ---------------------------------------------------------------------------


def test_check_house_skips_unconfigured_room_type(tmp_path: Path) -> None:
    """Photos with room types not in criteria config are skipped."""
    slug = "test-house"
    input_dir, output_dir = _setup_house(
        tmp_path,
        slug,
        photo_names=["hall.jpg"],
        classifications=[
            {
                "filename": "hall.jpg",
                "room_type": "hallway",
                "confidence": 0.9,
            }
        ],
    )

    mock_llm = MagicMock(spec=ILLMService)
    checker = VisionPhotoChecker(
        llm_service=mock_llm,
        input_dir=input_dir,
        output_dir=output_dir,
        criteria=SAMPLE_CRITERIA,
    )

    result = checker.check_house(slug)
    assert result.room_results == []
    mock_llm.classify_image.assert_not_called()


# ---------------------------------------------------------------------------
# Missing photo file
# ---------------------------------------------------------------------------


def test_check_house_missing_photo_file(tmp_path: Path) -> None:
    """Photos referenced in classifications but missing from disk are skipped."""
    slug = "test-house"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    # Create classification without corresponding photo
    cls_dir = output_dir / slug
    cls_dir.mkdir(parents=True)
    cls_file = cls_dir / "room_classifications.json"
    cls_file.write_text(
        json.dumps(
            _make_classifications_json(
                slug,
                [
                    {
                        "filename": "ghost.jpg",
                        "room_type": "kitchen",
                        "confidence": 0.9,
                    }
                ],
            )
        )
        + "\n",
        encoding="utf-8",
    )

    mock_llm = MagicMock(spec=ILLMService)
    checker = VisionPhotoChecker(
        llm_service=mock_llm,
        input_dir=input_dir,
        output_dir=output_dir,
        criteria=SAMPLE_CRITERIA,
    )

    result = checker.check_house(slug)
    assert result.room_results == []
    mock_llm.classify_image.assert_not_called()


# ---------------------------------------------------------------------------
# LLM missing feature in response — treated as not present
# ---------------------------------------------------------------------------


def test_missing_feature_in_llm_response(tmp_path: Path) -> None:
    """Features the LLM neglects to evaluate are treated as absent."""
    slug = "test-house"
    input_dir, output_dir = _setup_house(
        tmp_path,
        slug,
        photo_names=["kitchen.jpg"],
        classifications=[
            {
                "filename": "kitchen.jpg",
                "room_type": "kitchen",
                "confidence": 0.95,
            }
        ],
    )

    # LLM only returns 2 of 3 required features
    mock_llm = MagicMock(spec=ILLMService)
    mock_llm.classify_image.return_value = _mock_llm_response(
        [
            {"feature_name": "dishwasher", "present": True, "confidence": 0.9},
            {"feature_name": "oven", "present": True, "confidence": 0.85},
            # "sink" is missing from response
            {"feature_name": "island", "present": False, "confidence": 0.2},
            {
                "feature_name": "modern_cabinets",
                "present": True,
                "confidence": 0.7,
            },
        ]
    )

    checker = VisionPhotoChecker(
        llm_service=mock_llm,
        input_dir=input_dir,
        output_dir=output_dir,
        criteria=SAMPLE_CRITERIA,
    )
    result = checker.check_house(slug)

    room = result.room_results[0]
    sink_check = next(f for f in room.required_features if f.feature_name == "sink")
    assert sink_check.present is False
    assert sink_check.confidence == 0.0
    assert room.meets_required is False


# ---------------------------------------------------------------------------
# Multiple rooms in one house
# ---------------------------------------------------------------------------


def test_check_house_multiple_rooms(tmp_path: Path) -> None:
    """check_house processes multiple classified photos in one house."""
    slug = "multi-room"
    input_dir, output_dir = _setup_house(
        tmp_path,
        slug,
        photo_names=["kitchen.jpg", "bedroom.jpg"],
        classifications=[
            {
                "filename": "kitchen.jpg",
                "room_type": "kitchen",
                "confidence": 0.95,
            },
            {
                "filename": "bedroom.jpg",
                "room_type": "bedroom",
                "confidence": 0.9,
            },
        ],
    )

    def classify_side_effect(
        prompt: str,
        image_b64: str,
        media_type: str,
        response_model: type[LLMResponse],
    ) -> _PhotoCheckResult:
        if "kitchen" in prompt:
            return _mock_llm_response(
                [
                    {"feature_name": "dishwasher", "present": True, "confidence": 0.9},
                    {"feature_name": "oven", "present": True, "confidence": 0.8},
                    {"feature_name": "sink", "present": True, "confidence": 0.9},
                    {"feature_name": "island", "present": False, "confidence": 0.1},
                    {"feature_name": "modern_cabinets", "present": True, "confidence": 0.7},
                ]
            )
        return _mock_llm_response(
            [
                {"feature_name": "bed", "present": True, "confidence": 0.95},
                {"feature_name": "built_in_wardrobe", "present": False, "confidence": 0.3},
                {"feature_name": "natural_light", "present": True, "confidence": 0.8},
            ]
        )

    mock_llm = MagicMock(spec=ILLMService)
    mock_llm.classify_image.side_effect = classify_side_effect

    checker = VisionPhotoChecker(
        llm_service=mock_llm,
        input_dir=input_dir,
        output_dir=output_dir,
        criteria=SAMPLE_CRITERIA,
    )
    result = checker.check_house(slug)

    assert len(result.room_results) == 2
    assert mock_llm.classify_image.call_count == 2

    kitchen = next(r for r in result.room_results if r.room_type == RoomType.KITCHEN)
    bedroom = next(r for r in result.room_results if r.room_type == RoomType.BEDROOM)

    assert kitchen.meets_required is True
    assert bedroom.meets_required is True
    assert bedroom.meets_preferred is True


# ---------------------------------------------------------------------------
# Output file persistence
# ---------------------------------------------------------------------------


def test_check_house_saves_output(tmp_path: Path) -> None:
    """check_house writes results to photo_criteria.json."""
    slug = "test-house"
    input_dir, output_dir = _setup_house(
        tmp_path,
        slug,
        photo_names=["bed.jpg"],
        classifications=[
            {
                "filename": "bed.jpg",
                "room_type": "bedroom",
                "confidence": 0.9,
            }
        ],
    )

    mock_llm = MagicMock(spec=ILLMService)
    mock_llm.classify_image.return_value = _mock_llm_response(
        [
            {"feature_name": "bed", "present": True, "confidence": 0.95},
            {"feature_name": "built_in_wardrobe", "present": False, "confidence": 0.2},
            {"feature_name": "natural_light", "present": True, "confidence": 0.8},
        ]
    )

    checker = VisionPhotoChecker(
        llm_service=mock_llm,
        input_dir=input_dir,
        output_dir=output_dir,
        criteria=SAMPLE_CRITERIA,
    )
    checker.check_house(slug)

    output_file = output_dir / slug / "photo_criteria.json"
    assert output_file.exists()

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["slug"] == slug
    assert len(data["room_results"]) == 1
    assert data["room_results"][0]["photo_filename"] == "bed.jpg"


# ---------------------------------------------------------------------------
# Corrupt classifications file
# ---------------------------------------------------------------------------


def test_check_house_corrupt_classifications(tmp_path: Path) -> None:
    """Corrupt classifications file is handled gracefully (empty results)."""
    slug = "corrupt"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    cls_dir = output_dir / slug
    cls_dir.mkdir(parents=True)
    (cls_dir / "room_classifications.json").write_text("not json!", encoding="utf-8")

    mock_llm = MagicMock(spec=ILLMService)
    checker = VisionPhotoChecker(
        llm_service=mock_llm,
        input_dir=input_dir,
        output_dir=output_dir,
        criteria=SAMPLE_CRITERIA,
    )

    result = checker.check_house(slug)
    assert result.room_results == []
    mock_llm.classify_image.assert_not_called()

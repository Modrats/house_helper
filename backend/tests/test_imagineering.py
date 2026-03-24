"""Unit tests for the imagineering service."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import NamedTuple
from unittest.mock import MagicMock, patch

import pytest

from src.models.imagineering import ImagineeringPhoto, ImagineeringResult
from src.services.imagineering_service import FluxImagineeringService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_API_KEY = "test-key"
_FAKE_ENDPOINT = "https://flux.example.com/generate"
_FAKE_GUIDANCE = 15.0
_FAKE_SEED = 42

# 1x1 white PNG for testing (smallest valid PNG)
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
    b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_flux_response(image_bytes: bytes = _TINY_PNG) -> dict:
    """Build a fake FLUX API JSON response."""
    return {"data": [{"b64_json": base64.b64encode(image_bytes).decode("utf-8")}]}


def _setup_house(
    tmp_path: Path, slug: str, filenames: list[str], room_type: str = "bedroom"
) -> tuple[Path, Path]:
    """Create input photos and a classifications file in tmp_path.

    Returns:
        (input_dir, output_dir) paths.
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    photos_dir = input_dir / "houses" / slug / "photos"
    photos_dir.mkdir(parents=True)
    for name in filenames:
        (photos_dir / name).write_bytes(_TINY_PNG)

    classifications = {
        "slug": slug,
        "classifications": [
            {"filename": name, "room_type": room_type, "confidence": 0.9} for name in filenames
        ],
    }
    cls_dir = output_dir / "houses" / slug
    cls_dir.mkdir(parents=True)
    (cls_dir / "room_classifications.json").write_text(
        json.dumps(classifications, indent=2) + "\n", encoding="utf-8"
    )

    return input_dir, output_dir


def _make_service(input_dir: Path, output_dir: Path) -> FluxImagineeringService:
    """Create a FluxImagineeringService with test defaults."""
    return FluxImagineeringService(
        api_key=_FAKE_API_KEY,
        endpoint=_FAKE_ENDPOINT,
        input_dir=input_dir,
        output_dir=output_dir,
        guidance=_FAKE_GUIDANCE,
        default_seed=_FAKE_SEED,
    )


# ---------------------------------------------------------------------------
# Model serialization
# ---------------------------------------------------------------------------


class ModelSerializationCase(NamedTuple):
    """Test case for model round-trip serialization."""

    description: str
    photo: ImagineeringPhoto
    expected_room_type: str


MODEL_SERIALIZATION_CASES = [
    ModelSerializationCase(
        description="ImagineeringPhoto round-trips through dict serialization",
        photo=ImagineeringPhoto(
            filename="test.jpg",
            room_type="bedroom",
            prompt_used="test prompt",
            guidance_value=15.0,
            output_path="houses/test/imagineered/bedroom/test.png",
            timestamp="2026-03-24T00:00:00+00:00",
        ),
        expected_room_type="bedroom",
    ),
    ModelSerializationCase(
        description="ImagineeringPhoto preserves kitchen room type",
        photo=ImagineeringPhoto(
            filename="kitchen.jpg",
            room_type="kitchen",
            prompt_used="reimagine kitchen",
            guidance_value=20.0,
            output_path="houses/test/imagineered/kitchen/kitchen.png",
            timestamp="2026-03-24T12:00:00+00:00",
        ),
        expected_room_type="kitchen",
    ),
]


@pytest.mark.parametrize("description, photo, expected_room_type", MODEL_SERIALIZATION_CASES)
def test_model_serialization(
    description: str,
    photo: ImagineeringPhoto,
    expected_room_type: str,
) -> None:
    data = photo.model_dump()
    restored = ImagineeringPhoto(**data)
    assert restored.room_type == expected_room_type
    assert restored == photo


# ---------------------------------------------------------------------------
# ImagineeringResult container
# ---------------------------------------------------------------------------


class ResultContainerCase(NamedTuple):
    """Test case for ImagineeringResult."""

    description: str
    slug: str
    photo_count: int


RESULT_CONTAINER_CASES = [
    ResultContainerCase(
        description="empty result has no photos",
        slug="test-house",
        photo_count=0,
    ),
    ResultContainerCase(
        description="result holds multiple photos",
        slug="my-house",
        photo_count=3,
    ),
]


@pytest.mark.parametrize("description, slug, photo_count", RESULT_CONTAINER_CASES)
def test_result_container(description: str, slug: str, photo_count: int) -> None:
    photos = [
        ImagineeringPhoto(
            filename=f"photo_{i}.jpg",
            room_type="bedroom",
            prompt_used="prompt",
            guidance_value=15.0,
            output_path=f"houses/{slug}/imagineered/bedroom/photo_{i}.png",
            timestamp="2026-03-24T00:00:00+00:00",
        )
        for i in range(photo_count)
    ]
    result = ImagineeringResult(slug=slug, photos=photos)
    assert result.slug == slug
    assert len(result.photos) == photo_count


# ---------------------------------------------------------------------------
# Service — successful generation
# ---------------------------------------------------------------------------


class GenerationCase(NamedTuple):
    """Test case for successful image generation."""

    description: str
    filenames: list[str]
    room_type: str
    expected_output_count: int


GENERATION_CASES = [
    GenerationCase(
        description="single photo generates one output",
        filenames=["photo1.jpg"],
        room_type="bedroom",
        expected_output_count=1,
    ),
    GenerationCase(
        description="multiple photos each generate one output",
        filenames=["a.jpg", "b.png"],
        room_type="kitchen",
        expected_output_count=2,
    ),
]


@pytest.mark.parametrize(
    "description, filenames, room_type, expected_output_count", GENERATION_CASES
)
def test_generation_success(
    tmp_path: Path,
    description: str,
    filenames: list[str],
    room_type: str,
    expected_output_count: int,
) -> None:
    input_dir, output_dir = _setup_house(tmp_path, "test-house", filenames, room_type)
    service = _make_service(input_dir, output_dir)

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = _make_flux_response()

    with patch("src.services.imagineering_service.requests.post", return_value=mock_resp):
        result = service.imagineer_house("test-house")

    assert len(result.photos) == expected_output_count
    for photo in result.photos:
        assert photo.room_type == room_type
        assert photo.guidance_value == _FAKE_GUIDANCE
        output_file = output_dir / photo.output_path
        assert output_file.exists()


# ---------------------------------------------------------------------------
# Service — idempotent behavior
# ---------------------------------------------------------------------------


class IdempotentCase(NamedTuple):
    """Test case for idempotent generation skipping."""

    description: str
    already_done: list[str]
    all_files: list[str]
    expected_new_calls: int
    expected_total: int


IDEMPOTENT_CASES = [
    IdempotentCase(
        description="skips already-generated photos",
        already_done=["photo1.jpg"],
        all_files=["photo1.jpg", "photo2.jpg"],
        expected_new_calls=1,
        expected_total=2,
    ),
    IdempotentCase(
        description="no API calls when all photos are done",
        already_done=["a.jpg", "b.jpg"],
        all_files=["a.jpg", "b.jpg"],
        expected_new_calls=0,
        expected_total=2,
    ),
]


@pytest.mark.parametrize(
    "description, already_done, all_files, expected_new_calls, expected_total",
    IDEMPOTENT_CASES,
)
def test_idempotent_behavior(
    tmp_path: Path,
    description: str,
    already_done: list[str],
    all_files: list[str],
    expected_new_calls: int,
    expected_total: int,
) -> None:
    input_dir, output_dir = _setup_house(tmp_path, "test-house", all_files)
    service = _make_service(input_dir, output_dir)

    # Write pre-existing results
    existing_photos = [
        {
            "filename": name,
            "room_type": "bedroom",
            "prompt_used": "old prompt",
            "guidance_value": 15.0,
            "output_path": f"houses/test-house/imagineered/bedroom/{Path(name).stem}.png",
            "timestamp": "2026-03-24T00:00:00+00:00",
        }
        for name in already_done
    ]
    results_file = output_dir / "houses" / "test-house" / "imagineering_results.json"
    results_file.write_text(
        json.dumps({"slug": "test-house", "photos": existing_photos}, indent=2) + "\n",
        encoding="utf-8",
    )

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = _make_flux_response()

    with patch(
        "src.services.imagineering_service.requests.post", return_value=mock_resp
    ) as mock_post:
        result = service.imagineer_house("test-house")

    assert mock_post.call_count == expected_new_calls
    assert len(result.photos) == expected_total


# ---------------------------------------------------------------------------
# Service — API error handling
# ---------------------------------------------------------------------------


class APIErrorCase(NamedTuple):
    """Test case for API error handling."""

    description: str
    status_code: int
    is_retryable: bool


API_ERROR_CASES = [
    APIErrorCase(
        description="429 triggers retries then fails",
        status_code=429,
        is_retryable=True,
    ),
    APIErrorCase(
        description="500 triggers retries then fails",
        status_code=500,
        is_retryable=True,
    ),
    APIErrorCase(
        description="400 fails immediately without retry",
        status_code=400,
        is_retryable=False,
    ),
]


@pytest.mark.parametrize("description, status_code, is_retryable", API_ERROR_CASES)
def test_api_error_handling(
    tmp_path: Path,
    description: str,
    status_code: int,
    is_retryable: bool,
) -> None:
    input_dir, output_dir = _setup_house(tmp_path, "test-house", ["photo.jpg"])
    service = _make_service(input_dir, output_dir)

    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = status_code
    mock_resp.text = f"Error {status_code}"
    mock_resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")

    with (
        patch("src.services.imagineering_service.requests.post", return_value=mock_resp),
        patch("src.services.imagineering_service.time.sleep"),
        pytest.raises((RuntimeError, Exception)),
    ):
        service.imagineer_house("test-house")


# ---------------------------------------------------------------------------
# Service — missing classifications
# ---------------------------------------------------------------------------


class MissingDataCase(NamedTuple):
    """Test case for missing input data."""

    description: str
    has_classifications: bool
    expected_photo_count: int


MISSING_DATA_CASES = [
    MissingDataCase(
        description="no classifications file returns empty result",
        has_classifications=False,
        expected_photo_count=0,
    ),
]


@pytest.mark.parametrize(
    "description, has_classifications, expected_photo_count", MISSING_DATA_CASES
)
def test_missing_data(
    tmp_path: Path,
    description: str,
    has_classifications: bool,
    expected_photo_count: int,
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    if has_classifications:
        cls_dir = output_dir / "houses" / "test-house"
        cls_dir.mkdir(parents=True)
        (cls_dir / "room_classifications.json").write_text(
            json.dumps({"slug": "test-house", "classifications": []}) + "\n"
        )

    service = _make_service(input_dir, output_dir)
    result = service.imagineer_house("test-house")
    assert len(result.photos) == expected_photo_count


# ---------------------------------------------------------------------------
# Service — missing source photo
# ---------------------------------------------------------------------------


def test_missing_source_photo_skipped(tmp_path: Path) -> None:
    """Photos referenced in classifications but missing on disk are skipped."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    # Create classifications referencing a photo that doesn't exist on disk
    cls_dir = output_dir / "houses" / "test-house"
    cls_dir.mkdir(parents=True)
    (cls_dir / "room_classifications.json").write_text(
        json.dumps(
            {
                "slug": "test-house",
                "classifications": [
                    {"filename": "ghost.jpg", "room_type": "bedroom", "confidence": 0.9}
                ],
            }
        )
        + "\n"
    )

    # Don't create the photos directory at all
    service = _make_service(input_dir, output_dir)
    result = service.imagineer_house("test-house")
    assert len(result.photos) == 0


# ---------------------------------------------------------------------------
# Factory — create_imagineering_service
# ---------------------------------------------------------------------------


class FactoryEnvCase(NamedTuple):
    """Test case for create_imagineering_service env var validation."""

    description: str
    env_vars: dict[str, str]
    should_raise: bool


FACTORY_ENV_CASES = [
    FactoryEnvCase(
        description="missing FLUX_API_KEY raises RuntimeError",
        env_vars={"FLUX_ENDPOINT": "https://x", "FLUX_GUIDANCE": "15"},
        should_raise=True,
    ),
    FactoryEnvCase(
        description="missing FLUX_ENDPOINT raises RuntimeError",
        env_vars={"FLUX_API_KEY": "key", "FLUX_GUIDANCE": "15"},
        should_raise=True,
    ),
    FactoryEnvCase(
        description="missing FLUX_GUIDANCE raises RuntimeError",
        env_vars={"FLUX_API_KEY": "key", "FLUX_ENDPOINT": "https://x"},
        should_raise=True,
    ),
]


@pytest.mark.parametrize("description, env_vars, should_raise", FACTORY_ENV_CASES)
def test_factory_env_validation(
    description: str, env_vars: dict[str, str], should_raise: bool
) -> None:
    from src.core import create_imagineering_service

    with patch.dict("os.environ", env_vars, clear=True):
        if should_raise:
            with pytest.raises(RuntimeError, match="Missing required environment"):
                create_imagineering_service()

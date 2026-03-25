"""Unit tests for API routes, models, and app factory."""

from __future__ import annotations

import os
from typing import Any, NamedTuple
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.models import (
    FilterResultResponse,
    HealthResponse,
    HouseDetailResponse,
    HouseListItemResponse,
    PhotoResponse,
    RoomClassificationResponse,
)
from src.api.routes import get_repo
from src.models.house import FilterResult, House, HouseStatus
from src.models.room import Photo

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------


class ResponseModelCase(NamedTuple):
    """Test case for API response model construction."""

    description: str
    model_class: type
    kwargs: dict[str, Any]
    expected_field: str
    expected_value: Any


RESPONSE_MODEL_CASES = [
    ResponseModelCase(
        description="HealthResponse defaults to ok status",
        model_class=HealthResponse,
        kwargs={},
        expected_field="status",
        expected_value="ok",
    ),
    ResponseModelCase(
        description="HealthResponse has version 0.1.0",
        model_class=HealthResponse,
        kwargs={},
        expected_field="version",
        expected_value="0.1.0",
    ),
    ResponseModelCase(
        description="PhotoResponse stores filename",
        model_class=PhotoResponse,
        kwargs={"filename": "kitchen.jpg", "url": "/api/houses/villa/photos/kitchen.jpg"},
        expected_field="filename",
        expected_value="kitchen.jpg",
    ),
    ResponseModelCase(
        description="PhotoResponse room_type defaults to None",
        model_class=PhotoResponse,
        kwargs={"filename": "photo.jpg", "url": "/photos/photo.jpg"},
        expected_field="room_type",
        expected_value=None,
    ),
    ResponseModelCase(
        description="RoomClassificationResponse stores display name",
        model_class=RoomClassificationResponse,
        kwargs={
            "room_type": "living_room",
            "display_name": "Living Room",
            "photo_count": 3,
            "photos": ["lr1.jpg", "lr2.jpg", "lr3.jpg"],
        },
        expected_field="display_name",
        expected_value="Living Room",
    ),
    ResponseModelCase(
        description="FilterResultResponse computes passed correctly",
        model_class=FilterResultResponse,
        kwargs={"p1": {"garden": True}, "p2": {}, "excluded": {}, "passed": True},
        expected_field="passed",
        expected_value=True,
    ),
    ResponseModelCase(
        description="HouseListItemResponse stores slug",
        model_class=HouseListItemResponse,
        kwargs={
            "slug": "villa",
            "photo_count": 5,
            "status": "raw",
            "has_filter_results": False,
        },
        expected_field="slug",
        expected_value="villa",
    ),
    ResponseModelCase(
        description="HouseDetailResponse stores listing text",
        model_class=HouseDetailResponse,
        kwargs={
            "slug": "villa",
            "listing_text": "Beautiful villa",
            "status": "raw",
            "photo_count": 0,
            "room_count": 0,
            "filter_results": FilterResultResponse(p1={}, p2={}, excluded={}, passed=True),
            "photos": [],
        },
        expected_field="listing_text",
        expected_value="Beautiful villa",
    ),
]


def _make_mock_repo() -> MagicMock:
    """Create a mock HouseRepository with sensible defaults."""
    repo = MagicMock()
    repo.list_houses.return_value = []
    repo.get_room_classifications.return_value = {}
    repo.get_imagineered_photos.return_value = []
    repo.get_criteria_results.return_value = FilterResult()
    return repo


def _make_test_client(mock_repo: MagicMock) -> TestClient:
    """Create a TestClient with dependency-injected mock repository."""
    with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000"}):
        app = create_app()
    app.dependency_overrides[get_repo] = lambda: mock_repo
    return TestClient(app)


def _make_house(
    slug: str = "ikea_showroom",
    listing_text: str = "Beautiful showroom-style home with modern kitchen",
    status: HouseStatus = HouseStatus.RAW,
    photos: list[Photo] | None = None,
    filter_results: FilterResult | None = None,
) -> House:
    """Create a House for testing routes."""
    return House(
        slug=slug,
        listing_text=listing_text,
        status=status,
        photos=photos or [],
        filter_results=filter_results or FilterResult(),
    )


# ===========================================================================
# Happy path
# ===========================================================================

# --- Response models ---


@pytest.mark.parametrize(
    "description, model_class, kwargs, expected_field, expected_value",
    RESPONSE_MODEL_CASES,
    ids=[c.description for c in RESPONSE_MODEL_CASES],
)
def test_response_model_construction(
    description: str,
    model_class: type,
    kwargs: dict,
    expected_field: str,
    expected_value: Any,
) -> None:
    """API response models construct with expected field values."""
    # Act
    model = model_class(**kwargs)

    # Assert
    assert getattr(model, expected_field) == expected_value


def test_response_model_serialization() -> None:
    """API models serialize to dict correctly."""
    # Arrange
    model = PhotoResponse(
        filename="kitchen.jpg",
        url="/api/houses/villa/photos/kitchen.jpg",
        room_type="kitchen",
        confidence=0.95,
        imagineered_url="/api/houses/villa/imagineered/kitchen.jpg",
    )

    # Act
    data = model.model_dump()

    # Assert
    assert data["filename"] == "kitchen.jpg"
    assert data["confidence"] == 0.95
    assert data["imagineered_url"] == "/api/houses/villa/imagineered/kitchen.jpg"


# --- create_app ---


def test_create_app_returns_fastapi_instance() -> None:
    """create_app returns a FastAPI app with correct metadata."""
    # Act
    with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000"}):
        app = create_app()

    # Assert
    assert app.title == "House Helper API"
    assert app.version == "0.1.0"


def test_create_app_with_multiple_origins() -> None:
    """create_app accepts comma-separated CORS origins."""
    # Act
    with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000,https://example.com"}):
        app = create_app()

    # Assert
    assert app is not None


# --- GET /health ---


def test_health_check() -> None:
    """GET /health returns ok status."""
    # Arrange
    mock_repo = _make_mock_repo()
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


# --- GET /api/houses ---


def test_list_houses_returns_summary() -> None:
    """GET /api/houses returns summary info for each house."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.list_houses.return_value = ["ikea_showroom"]
    mock_repo.get_house.return_value = _make_house(
        photos=[Photo(filename="kitchen.jpg", path="photos/kitchen.jpg")]
    )
    mock_repo.get_photos.return_value = ["/data/input/ikea_showroom/photos/kitchen.jpg"]
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "ikea_showroom"
    assert data[0]["photo_count"] == 1
    assert data[0]["thumbnail_url"] is not None


# --- GET /api/houses/{slug} ---


def test_get_house_detail() -> None:
    """GET /api/houses/{slug} returns full house detail."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_house.return_value = _make_house(listing_text="Modern villa with garden")
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/ikea_showroom")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "ikea_showroom"
    assert data["listing_text"] == "Modern villa with garden"
    assert data["filter_results"]["passed"] is True


# --- GET /api/houses/{slug}/rooms ---


def test_get_room_classifications() -> None:
    """GET /api/houses/{slug}/rooms returns room classifications."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_house.return_value = _make_house()
    mock_repo.get_room_classifications.return_value = {
        "kitchen": ["k1.jpg", "k2.jpg"],
        "bedroom": ["b1.jpg"],
    }
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/ikea_showroom/rooms")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    room_types = {item["room_type"] for item in data}
    assert room_types == {"bedroom", "kitchen"}


# --- GET /api/houses/{slug}/photos ---


def test_get_photos_returns_all() -> None:
    """GET /api/houses/{slug}/photos returns all photos."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_house.return_value = _make_house(
        photos=[
            Photo(filename="kitchen.jpg", path="photos/kitchen.jpg"),
            Photo(filename="garden.jpg", path="photos/garden.jpg"),
        ]
    )
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/ikea_showroom/photos")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_photos_filters_by_room_type() -> None:
    """GET /api/houses/{slug}/photos?roomType=kitchen filters photos."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_house.return_value = _make_house(
        photos=[
            Photo(filename="kitchen.jpg", path="photos/kitchen.jpg"),
            Photo(filename="garden.jpg", path="photos/garden.jpg"),
        ]
    )
    mock_repo.get_room_classifications.return_value = {
        "kitchen": ["kitchen.jpg"],
        "garden": ["garden.jpg"],
    }
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/ikea_showroom/photos?roomType=kitchen")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_get_photos_includes_imagineered_url() -> None:
    """GET /api/houses/{slug}/photos includes imagineered URLs when available."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_house.return_value = _make_house(
        photos=[Photo(filename="kitchen.jpg", path="photos/kitchen.jpg")]
    )
    mock_repo.get_imagineered_photos.return_value = [
        "/data/output/ikea_showroom/imagineered/kitchen.jpg"
    ]
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/ikea_showroom/photos")

    # Assert
    data = response.json()
    assert data[0]["imagineered_url"] is not None
    assert "imagineered" in data[0]["imagineered_url"]


# --- GET /api/houses/{slug}/photos/{filename} ---


def test_get_photo_serves_bytes() -> None:
    """GET /api/houses/{slug}/photos/{filename} serves photo bytes."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_photo_bytes.return_value = b"\x89PNG fake photo"
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/ikea_showroom/photos/kitchen.jpg")

    # Assert
    assert response.status_code == 200
    assert response.content == b"\x89PNG fake photo"
    assert "image/jpeg" in response.headers["content-type"]


# --- GET /api/houses/{slug}/imagineered/{filename} ---


def test_get_imagineered_photo_serves_bytes() -> None:
    """GET /api/houses/{slug}/imagineered/{filename} serves imagineered bytes."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_imagineered_photo_bytes.return_value = b"\x89PNG imagineered"
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/ikea_showroom/imagineered/kitchen.jpg")

    # Assert
    assert response.status_code == 200
    assert response.content == b"\x89PNG imagineered"


# ===========================================================================
# Edge cases
# ===========================================================================

# --- GET /api/houses ---


def test_list_houses_empty() -> None:
    """GET /api/houses returns empty list when no houses exist."""
    # Arrange
    mock_repo = _make_mock_repo()
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses")

    # Assert
    assert response.status_code == 200
    assert response.json() == []


def test_list_houses_skips_unloadable() -> None:
    """GET /api/houses skips houses that raise FileNotFoundError."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.list_houses.return_value = ["good_house", "bad_house"]
    mock_repo.get_house.side_effect = [
        _make_house(slug="good_house"),
        FileNotFoundError("bad_house not found"),
    ]
    mock_repo.get_photos.return_value = []
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "good_house"


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- GET /api/houses/{slug} ---


def test_get_house_not_found() -> None:
    """GET /api/houses/{slug} returns 404 for unknown house."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_house.side_effect = FileNotFoundError("not found")
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/nonexistent")

    # Assert
    assert response.status_code == 404


# --- GET /api/houses/{slug}/rooms ---


def test_get_room_classifications_not_found() -> None:
    """GET /api/houses/{slug}/rooms returns 404 for unknown house."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_house.side_effect = FileNotFoundError("not found")
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/nonexistent/rooms")

    # Assert
    assert response.status_code == 404


# --- GET /api/houses/{slug}/photos ---


def test_get_photos_not_found() -> None:
    """GET /api/houses/{slug}/photos returns 404 for unknown house."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_house.side_effect = FileNotFoundError("not found")
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/nonexistent/photos")

    # Assert
    assert response.status_code == 404


# --- GET /api/houses/{slug}/photos/{filename} ---


def test_get_photo_not_found() -> None:
    """GET /api/houses/{slug}/photos/{filename} returns 404 for missing photo."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_photo_bytes.side_effect = FileNotFoundError("not found")
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/ikea_showroom/photos/missing.jpg")

    # Assert
    assert response.status_code == 404


# --- GET /api/houses/{slug}/imagineered/{filename} ---


def test_get_imagineered_photo_not_found() -> None:
    """GET /api/houses/{slug}/imagineered/{filename} returns 404 for missing."""
    # Arrange
    mock_repo = _make_mock_repo()
    mock_repo.get_imagineered_photo_bytes.side_effect = FileNotFoundError("not found")
    client = _make_test_client(mock_repo)

    # Act
    response = client.get("/api/houses/ikea_showroom/imagineered/missing.jpg")

    # Assert
    assert response.status_code == 404
